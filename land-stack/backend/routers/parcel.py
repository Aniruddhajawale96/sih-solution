"""
routers/parcel.py — Parcel domain router.

Endpoints
---------
GET  /parcels/{ulpin}   — Fetch a single parcel by ULPIN.
                          CITIZEN → ParcelPublic (no polygon geometry).
                          Officer / Admin → ParcelInternal (all fields + GeoJSON geom).
GET  /parcels/search    — Filtered, paginated parcel search.
                          Supports: q (free-text on district/village), state_code,
                          district, bbox (minx,miny,maxx,maxy via PostGIS ST_Intersects).
POST /parcels           — Create a new parcel (REV_OFF, STATE_ADMIN, NATL_ADMIN only).
                          Writes CREATE_PARCEL audit entry inside the same transaction.

Requirements: 8.1, 8.2, 8.3, 8.4
"""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.functions import ST_GeomFromGeoJSON, ST_Intersects, ST_MakeEnvelope
from geoalchemy2 import WKBElement
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit
from core.database import get_db
from core.rbac import VALID_ROLES, UserClaims, check_jurisdiction, get_current_user, require_role
from core.response_schemas import ParcelCreate, ParcelInternal, ParcelPublic
from core.schemas import Envelope, ok
from models.parcel import Parcel

try:
    # geoalchemy2 ≥ 0.14 ships a helper; fall back to shapely for older installs.
    from geoalchemy2.shape import to_shape  # type: ignore[import-untyped]

    def _geom_to_geojson(element: WKBElement) -> str:
        """Convert a GeoAlchemy2 WKBElement to a GeoJSON string."""
        shape = to_shape(element)
        return json.dumps(shape.__geo_interface__)

except ImportError:  # pragma: no cover
    def _geom_to_geojson(element: WKBElement) -> str:  # type: ignore[misc]
        """Fallback: return hex WKB as a plain string."""
        return str(element)


router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_ROLES = list(VALID_ROLES)
_WRITE_ROLES = ["REV_OFF", "STATE_ADMIN", "NATL_ADMIN"]
_CITIZEN_ROLE = "CITIZEN"


def _to_public(parcel: Parcel) -> ParcelPublic:
    """Serialise a Parcel ORM instance to its public (citizen-facing) schema."""
    return ParcelPublic.model_validate(parcel)


def _to_internal(parcel: Parcel) -> ParcelInternal:
    """Serialise a Parcel ORM instance to its internal (officer-facing) schema.

    Converts the PostGIS WKBElement to a GeoJSON string so the Pydantic model
    can carry it as a plain ``str`` field.
    """
    geom_json: str | None = None
    if parcel.geom is not None:
        try:
            geom_json = _geom_to_geojson(parcel.geom)
        except Exception:
            geom_json = None  # degrade gracefully; geometry present but unreadable

    return ParcelInternal(
        ulpin=parcel.ulpin,
        state_code=parcel.state_code,
        district=parcel.district,
        village_or_city=parcel.village_or_city,
        area_sqm=parcel.area_sqm,
        survey_or_khasra_no=parcel.survey_or_khasra_no,
        tehsil=parcel.tehsil,
        source_system=parcel.source_system,
        last_synced_at=parcel.last_synced_at,
        geom=geom_json,
    )


# ---------------------------------------------------------------------------
# GET /parcels/search   — MUST be declared before /{ulpin} to avoid shadowing
# ---------------------------------------------------------------------------

@router.get(
    "/search",
    response_model=Envelope[list[ParcelPublic]],
    summary="Search parcels",
    description=(
        "Filtered, paginated parcel search. "
        "Open to all authenticated roles. "
        "Officers receive ParcelInternal fields; citizens receive ParcelPublic."
    ),
)
async def search_parcels(
    q: Annotated[str | None, Query(description="Free-text search on district or village_or_city")] = None,
    state_code: Annotated[str | None, Query(description="Filter by state code")] = None,
    district: Annotated[str | None, Query(description="Filter by district name")] = None,
    bbox: Annotated[
        str | None,
        Query(description="Bounding box filter as 'minx,miny,maxx,maxy' (WGS84 decimal degrees)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Max records to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    user: UserClaims = Depends(require_role(_ALL_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope:
    """Return a paginated list of parcels matching the given filters.

    - ``q``: case-insensitive substring match against ``district`` OR ``village_or_city``.
    - ``state_code``: exact match.
    - ``district``: exact match.
    - ``bbox``: PostGIS ``ST_Intersects`` against an envelope constructed from the
      four comma-separated coordinates.

    The response schema depends on the caller's role:
    CITIZEN → list of ``ParcelPublic``; officers/admins → list of ``ParcelInternal``.
    """
    stmt = select(Parcel)

    # --- free-text filter -------------------------------------------------------
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Parcel.district.ilike(pattern),
                Parcel.village_or_city.ilike(pattern),
            )
        )

    # --- exact filters ----------------------------------------------------------
    if state_code:
        stmt = stmt.where(Parcel.state_code == state_code)

    if district:
        stmt = stmt.where(Parcel.district == district)

    # --- spatial bbox filter ----------------------------------------------------
    if bbox:
        parts = bbox.split(",")
        if len(parts) != 4:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="bbox must be 'minx,miny,maxx,maxy'",
            )
        try:
            minx, miny, maxx, maxy = (float(p.strip()) for p in parts)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="bbox coordinates must be numeric decimal-degree values",
            )
        envelope = ST_MakeEnvelope(minx, miny, maxx, maxy, 4326)
        stmt = stmt.where(ST_Intersects(Parcel.geom, envelope))

    # --- pagination -------------------------------------------------------------
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    parcels: list[Parcel] = list(result.scalars().all())

    if user.role == _CITIZEN_ROLE:
        data = [_to_public(p) for p in parcels]
        return ok(data)

    # Officers receive the richer internal schema.
    # Type-widen to list[ParcelPublic] so the declared response_model is satisfied;
    # ParcelInternal is a subclass so serialisation includes the extra fields.
    data = [_to_internal(p) for p in parcels]  # type: ignore[assignment]
    return ok(data)


# ---------------------------------------------------------------------------
# GET /parcels/{ulpin}
# ---------------------------------------------------------------------------

@router.get(
    "/{ulpin}",
    response_model=None,
    summary="Get parcel by ULPIN",
)
async def get_parcel(
    ulpin: str,
    user: UserClaims = Depends(require_role(_ALL_ROLES)),
    _jx: None = Depends(check_jurisdiction),
    db: AsyncSession = Depends(get_db),
) -> Envelope:
    """Fetch a single parcel.

    - **CITIZEN**: receives ``ParcelPublic`` (no polygon geometry).
    - **Officers / Admins**: receives ``ParcelInternal`` (all fields including GeoJSON geometry).

    ``check_jurisdiction`` enforces that state-scoped officers can only access
    parcels within their own state.
    """
    parcel: Parcel | None = await db.get(Parcel, ulpin)
    if parcel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parcel {ulpin!r} not found",
        )

    if user.role == _CITIZEN_ROLE:
        return ok(_to_public(parcel))

    return ok(_to_internal(parcel))


# ---------------------------------------------------------------------------
# POST /parcels
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=Envelope[ParcelInternal],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new parcel",
)
async def create_parcel(
    body: ParcelCreate,
    user: UserClaims = Depends(require_role(_WRITE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope:
    """Create a new parcel record.

    Requires role ``REV_OFF``, ``STATE_ADMIN``, or ``NATL_ADMIN``.

    - Converts the GeoJSON string in ``body.geom`` to a PostGIS geometry via
      ``ST_GeomFromGeoJSON``.
    - Writes a ``CREATE_PARCEL`` audit entry inside the same DB transaction
      before committing.
    - Returns 201 with the newly created parcel as ``ParcelInternal``.
    """
    # Check for duplicate ULPIN.
    existing = await db.get(Parcel, body.ulpin)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Parcel with ULPIN {body.ulpin!r} already exists",
        )

    # Convert GeoJSON → PostGIS geometry expression.
    geom_expr = ST_GeomFromGeoJSON(body.geom)

    parcel = Parcel(
        ulpin=body.ulpin,
        state_code=body.state_code,
        district=body.district,
        tehsil=body.tehsil,
        village_or_city=body.village_or_city,
        area_sqm=body.area_sqm,
        survey_or_khasra_no=body.survey_or_khasra_no,
        source_system=body.source_system,
        geom=geom_expr,
    )
    db.add(parcel)

    # Flush so the row is visible to audit but not yet committed.
    await db.flush()

    # Write the audit entry inside the same open transaction.
    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="CREATE_PARCEL",
        resource_type="parcel",
        resource_id=body.ulpin,
    )

    await db.commit()

    # Reload from DB so the ORM-managed geom field is populated correctly.
    await db.refresh(parcel)

    return ok(_to_internal(parcel))
