"""
SQLAlchemy model for the `encumbrances` table (Essential Layer).

Multiple encumbrances can exist per parcel; `id` is an auto-increment PK.
`institution` is shown publicly — required by transparency rules.
"""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class Encumbrance(Base):
    __tablename__ = "encumbrances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ulpin: Mapped[str] = mapped_column(
        String, ForeignKey("parcels.ulpin"), nullable=False
    )
    # Mortgage / Lien / Court Case
    type: Mapped[str] = mapped_column(String, nullable=False)
    # Shown publicly — transparency requirement (see DATA_SCHEMA.md)
    institution: Mapped[str] = mapped_column(String, nullable=False)
    # Active / Cleared
    status: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
