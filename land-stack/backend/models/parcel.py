"""
SQLAlchemy model for the `parcels` table (Base Layer).

Geometry column uses GeoAlchemy2 with SRID 4326 (WGS84) per DATA_SCHEMA.md.
"""

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class Parcel(Base):
    __tablename__ = "parcels"

    ulpin: Mapped[str] = mapped_column(String, primary_key=True)
    state_code: Mapped[str] = mapped_column(String, nullable=False)
    district: Mapped[str] = mapped_column(String, nullable=False)
    tehsil: Mapped[str | None] = mapped_column(String, nullable=True)
    village_or_city: Mapped[str] = mapped_column(String, nullable=False)
    geom: Mapped[object] = mapped_column(
        Geometry("POLYGON", srid=4326), nullable=False
    )
    area_sqm: Mapped[float] = mapped_column(Float, nullable=False)
    survey_or_khasra_no: Mapped[str] = mapped_column(String, nullable=False)
    source_system: Mapped[str] = mapped_column(String, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
