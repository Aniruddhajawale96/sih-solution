"""
SQLAlchemy model for the `users` table.

Roles (7 RBAC roles): CITIZEN, REV_OFF, REG_OFF, PLAN_OFF, TAX_OFF,
STATE_ADMIN, NATL_ADMIN.

`jurisdiction` is the state_code for state-scoped roles; NULL for CITIZEN
and NATL_ADMIN who have no geographic restriction.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String, primary_key=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
