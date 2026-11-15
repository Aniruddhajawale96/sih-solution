from __future__ import annotations
from sqlalchemy import Column, Date, ForeignKey, Integer, String
from core.database import Base


class Tax(Base):
    __tablename__ = "tax"

    ulpin = Column(String, ForeignKey("parcels.ulpin"), primary_key=True)
    assessment_id = Column(String, nullable=False)
    annual_tax = Column(Integer, nullable=False)
    last_paid_date = Column(Date, nullable=True)
    payment_status = Column(String, nullable=False)   # Paid / Overdue
    arrears = Column(Integer, nullable=False, default=0)
