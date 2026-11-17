"""
Import all models here so they register with Base.metadata before Alembic
autogenerate or table creation runs.
"""

from .audit_log import AuditLog
from .building_permission import BuildingPermission
from .encumbrance import Encumbrance
from .parcel import Parcel
from .registration import Registration
from .ror import Ror
from .state_adapter import StateAdapterConfig
from .tax import Tax
from .users import User
from .workflow import CitizenServiceRequest, WorkflowTask
from .zoning import Zoning

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
