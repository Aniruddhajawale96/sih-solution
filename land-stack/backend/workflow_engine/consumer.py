"""
workflow_engine/consumer.py — Async Redis pub/sub event consumer.

Subscribes to domain events published by routers and triggers follow-on
workflow actions:

  registration.completed → create a WorkflowTask(type=MUTATION, role=REV_OFF)
  mutation.approved       → reassess tax for the parcel; write audit REASSESS_TAX

Message payload (JSON):
  registration.completed: {"ulpin": "<ULPIN>", ...}
  mutation.approved:       {"ulpin": "<ULPIN>", "area_sqm": <float>, ...}

Requirements: 9.1, 9.2, 9.3
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.audit import write_audit
from core.database import AsyncSessionLocal
from models.tax import Tax
from models.workflow import WorkflowTask

logger = logging.getLogger(__name__)

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

_CHANNELS = ("registration.completed", "mutation.approved")


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def _handle_registration_completed(
    payload: dict[str, Any],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Create a pending MUTATION WorkflowTask for the REV_OFF role.

    Requirements: 9.1
    """
    ulpin: str | None = payload.get("ulpin")
    if not ulpin:
        logger.warning("registration.completed: missing ulpin in payload %s", payload)
        return

    async with session_factory() as db:
        try:
            task = WorkflowTask(
                ulpin=ulpin,
                task_type="MUTATION",
                assigned_role="REV_OFF",
                status="pending",
            )
            db.add(task)
            await db.commit()
            logger.info(
                "registration.completed: created MUTATION WorkflowTask for ulpin=%s", ulpin
            )
        except Exception:
            await db.rollback()
            logger.exception(
                "registration.completed: failed to create WorkflowTask for ulpin=%s", ulpin
            )
            raise


async def _handle_mutation_approved(
    payload: dict[str, Any],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Reassess tax for the parcel and write an audit entry.

    Tax reassessment rule (placeholder):
      If the Tax row has ``arrears > 0``, recalculate ``annual_tax`` as
      ``area_sqm * 10`` where ``area_sqm`` comes from the event payload (or
      falls back to the existing ``annual_tax`` if not provided).

    Requirements: 9.2
    """
    ulpin: str | None = payload.get("ulpin")
    if not ulpin:
        logger.warning("mutation.approved: missing ulpin in payload %s", payload)
        return

    area_sqm: float | None = payload.get("area_sqm")

    async with session_factory() as db:
        try:
            result = await db.execute(select(Tax).where(Tax.ulpin == ulpin))
            tax_row: Tax | None = result.scalar_one_or_none()

            if tax_row is None:
                logger.warning(
                    "mutation.approved: no Tax row for ulpin=%s — skipping reassessment", ulpin
                )
                return

            if tax_row.arrears > 0 and area_sqm is not None:
                tax_row.annual_tax = int(area_sqm * 10)
                logger.info(
                    "mutation.approved: reassessed annual_tax=%s for ulpin=%s",
                    tax_row.annual_tax,
                    ulpin,
                )

            await write_audit(
                db=db,
                actor_user="system",
                actor_role="SYSTEM",
                action="REASSESS_TAX",
                resource_type="tax",
                resource_id=ulpin,
            )
            await db.commit()
            logger.info("mutation.approved: audit written for ulpin=%s", ulpin)
        except Exception:
            await db.rollback()
            logger.exception(
                "mutation.approved: failed to reassess tax for ulpin=%s", ulpin
            )
            raise


# ---------------------------------------------------------------------------
# Main consumer loop
# ---------------------------------------------------------------------------

_CHANNEL_HANDLERS = {
    "registration.completed": _handle_registration_completed,
    "mutation.approved": _handle_mutation_approved,
}


async def start_consumer(
    redis_client: aioredis.Redis | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> None:  # pragma: no cover
    """Start the Redis pub/sub consumer loop.

    Parameters
    ----------
    redis_client:
        An already-constructed ``redis.asyncio.Redis`` instance. When
        ``None`` (default), one is created from ``REDIS_URL``. Pass an
        explicit client in tests to inject a fake.
    session_factory:
        An ``async_sessionmaker`` for opening DB sessions. Defaults to
        ``AsyncSessionLocal`` from ``core.database``. Pass a custom factory
        in tests to inject an in-memory session.
    """
    if session_factory is None:
        session_factory = AsyncSessionLocal  # type: ignore[assignment]

    own_client = redis_client is None
    if own_client:
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

    try:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(*_CHANNELS)
        logger.info("Workflow engine consumer subscribed to: %s", _CHANNELS)

        async for raw_message in pubsub.listen():
            if raw_message["type"] != "message":
                # Skip subscribe confirmation and other non-data messages.
                continue

            channel: str = raw_message["channel"]
            handler = _CHANNEL_HANDLERS.get(channel)
            if handler is None:
                logger.debug("No handler registered for channel %s", channel)
                continue

            try:
                payload: dict[str, Any] = json.loads(raw_message["data"])
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "consumer: could not parse JSON from channel %s: %r",
                    channel,
                    raw_message["data"],
                )
                continue

            try:
                await handler(payload, session_factory)
            except Exception:
                # Log but do not crash the consumer loop — a single bad
                # message should not bring down the background task.
                logger.exception(
                    "consumer: unhandled error processing message on %s", channel
                )
    finally:
        if own_client:
            await redis_client.aclose()
