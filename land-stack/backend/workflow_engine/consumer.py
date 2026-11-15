"""
workflow_engine/consumer.py — Async Redis event consumer.

Subscribes to domain events published by routers and triggers follow-on
workflow actions (e.g. creating a mutation task when a deed is registered).

This is a stub implementation. The real handler logic is added in task 10.1.
"""

import logging

logger = logging.getLogger(__name__)


async def start_consumer() -> None:  # pragma: no cover
    """
    Start the Redis pub/sub consumer loop.

    Subscribes to ``registration.completed`` and ``mutation.approved``.
    This stub exits immediately; task 10.1 replaces it with the real loop.
    """
    logger.info("Workflow engine consumer started (stub — no-op)")
