"""
SQLAlchemy model for the `building_permissions` table (Essential Layer).

Multiple permits can exist per parcel; `id` is an auto-increment PK.
`architect_ref` is nullable — older records may lack this field.
"""

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class BuildingPermission(Base):
    __tablename__ = "building_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ulpin: Mapped[str] = mapped_column(
        String, ForeignKey("parcels.ulpin"), nullable=False
    )
    approval_no: Mapped[str] = mapped_column(String, nullable=False)
    approved_built_up_area: Mapped[float] = mapped_column(Float, nullable=False)
    approval_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Approved / Under Review / Rejected
    status: Mapped[str] = mapped_column(String, nullable=False)
    architect_ref: Mapped[str | None] = mapped_column(String, nullable=True)
