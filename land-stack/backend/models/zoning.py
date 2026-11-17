"""
SQLAlchemy model for the `zoning` table (Essential Layer — Master Plan).

One zoning record per parcel; `ulpin` is both PK and FK to `parcels.ulpin`.
`violation_flag` is set to True when `far_existing > far_permitted`; this
invariant is enforced by the router/ML layer, not a DB constraint.
"""

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Zoning(Base):
    __tablename__ = "zoning"

    ulpin: Mapped[str] = mapped_column(
        String, ForeignKey("parcels.ulpin"), primary_key=True
    )
    # Residential / Commercial / Agricultural
    master_plan_zone: Mapped[str] = mapped_column(String, nullable=False)
    permissible_use: Mapped[str] = mapped_column(String, nullable=False)
    far_permitted: Mapped[float] = mapped_column(Float, nullable=False)
    far_existing: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # True when far_existing > far_permitted
    violation_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
