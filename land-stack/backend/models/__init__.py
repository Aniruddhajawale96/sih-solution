"""
Import all models here so they register with Base.metadata before Alembic
autogenerate or table creation runs.
"""

from backend.models.audit_log import AuditLog
from backend.models.building_permission import BuildingPermission
from backend.models.encumbrance import Encumbrance
from backend.models.parcel import Parcel
from backend.models.registration import Registration
from backend.models.ror import Ror
from backend.models.state_adapter import StateAdapterConfig
from backend.models.tax import Tax
from backend.models.users import User
from backend.models.workflow import CitizenServiceRequest, WorkflowTask
from backend.models.zoning import Zoning

__all__ = [
    "Parcel",
    "User",
    "AuditLog",
    "Ror",
    "Registration",
    "Encumbrance",
    "Zoning",
    "BuildingPermission",
    "Tax",
    "WorkflowTask",
    "CitizenServiceRequest",
    "StateAdapterConfig",
]
