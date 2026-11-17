"""
SQLAlchemy model for the `state_adapter_configs` table.

Maps state-specific field names and units to the canonical LandStack schema,
enabling the ingestion pipeline to normalise data from any state's source system.
"""

from sqlalchemy import Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class StateAdapterConfig(Base):
    __tablename__ = "state_adapter_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_field_name: Mapped[str] = mapped_column(String, nullable=False)
    canonical_field_name: Mapped[str] = mapped_column(String, nullable=False)
    # Multiply source numeric value by this factor to get canonical SI units.
    # e.g. 4046.86 converts acres → sq.m; 1.0 means no conversion needed.
    unit_conversion_factor: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )
    language_code: Mapped[str] = mapped_column(String, nullable=False, default="en")
