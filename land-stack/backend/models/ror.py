"""
SQLAlchemy model for the `ror` table (Record of Rights — Essential Layer).

One row per parcel; `ulpin` is both PK and FK to `parcels.ulpin`.
"""

from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Ror(Base):
    __tablename__ = "ror"

    ulpin: Mapped[str] = mapped_column(
        String, ForeignKey("parcels.ulpin"), primary_key=True
    )
    owner_name: Mapped[str] = mapped_column(String, nullable=False)
    # Freehold / Leasehold / Patta
    tenure_type: Mapped[str] = mapped_column(String, nullable=False)
    khatauni_no: Mapped[str] = mapped_column(String, nullable=False)
    # Residential / Commercial / Agricultural
    land_use_type: Mapped[str] = mapped_column(String, nullable=False)
    # Clear / Pending
    mutation_status: Mapped[str] = mapped_column(String, nullable=False)
    last_updated: Mapped[date] = mapped_column(Date, nullable=False)
