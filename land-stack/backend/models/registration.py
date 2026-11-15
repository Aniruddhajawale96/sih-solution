"""
SQLAlchemy model for the `registrations` table (Essential Layer).

Multiple registrations can exist per parcel; `id` is an auto-increment PK.
`transaction_value` is withheld from public (CITIZEN) responses — masking
is enforced at the schema/serialization layer, not here.
"""

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class Registration(Base):
    __tablename__ = "registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ulpin: Mapped[str] = mapped_column(
        String, ForeignKey("parcels.ulpin"), nullable=False
    )
    deed_no: Mapped[str] = mapped_column(String, nullable=False)
    # Sale / Gift / Lease
    deed_type: Mapped[str] = mapped_column(String, nullable=False)
    registration_date: Mapped[date] = mapped_column(Date, nullable=False)
    sro_office: Mapped[str] = mapped_column(String, nullable=False)
    buyer: Mapped[str] = mapped_column(String, nullable=False)
    seller: Mapped[str] = mapped_column(String, nullable=False)
    # Hidden from CITIZEN via RorPublic / RegistrationPublic schemas
    transaction_value: Mapped[int] = mapped_column(Integer, nullable=False)
    stamp_duty_paid: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
