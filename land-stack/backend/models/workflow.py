"""
SQLAlchemy models for workflow tables.

WorkflowTask — tracks pending/approved/rejected mutations, tax reassessments,
and zoning approvals routed to the appropriate officer role.

CitizenServiceRequest — citizen-submitted requests for ownership certificates,
mutation requests, and encumbrance certificates.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ulpin: Mapped[str] = mapped_column(
        String, ForeignKey("parcels.ulpin"), nullable=False
    )
    # One of: MUTATION, TAX, ZONING
    task_type: Mapped[str] = mapped_column(String, nullable=False)
    # One of: REV_OFF, TAX_OFF, PLAN_OFF
    assigned_role: Mapped[str] = mapped_column(String, nullable=False)
    # One of: pending, approved, rejected
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    comment: Mapped[str | None] = mapped_column(String, nullable=True)


class CitizenServiceRequest(Base):
    __tablename__ = "citizen_service_requests"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ulpin: Mapped[str] = mapped_column(
        String, ForeignKey("parcels.ulpin"), nullable=False
    )
    citizen_username: Mapped[str] = mapped_column(
        String, ForeignKey("users.username"), nullable=False
    )
    # One of: OWNERSHIP_CERT, MUTATION_REQ, ENCUMBRANCE_CERT
    service_type: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="submitted")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
