"""
Seed loader — loads all seed data files into the Land Stack database.
Run from backend/ directory:  python -m scripts.seed_loader
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://landstack:landstack@localhost:5432/landstack",
)
SEED_DIR = Path(__file__).parent.parent.parent / "seed-data"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

from models.parcel import Parcel
from models.users import User
from models.ror import Ror
from models.registration import Registration
from models.encumbrance import Encumbrance
from models.zoning import Zoning
from models.building_permission import BuildingPermission
from models.tax import Tax
from models.state_adapter import StateAdapterConfig
from core.auth import hash_password


async def load_state_adapter(session) -> dict[str, list[dict]]:
    path = SEED_DIR / "state_adapter_config.json"
    records = json.loads(path.read_text())
    for rec in records:
        stmt = pg_insert(StateAdapterConfig).values(**rec).on_conflict_do_nothing()
        await session.execute(stmt)
    mapping: dict[str, list[dict]] = {}
    for rec in records:
        mapping.setdefault(rec["state_code"], []).append(rec)
    return mapping


def apply_conversions(record: dict, adapter_map: dict) -> dict:
    state_code = record.get("state_code", "")
    result = dict(record)
    for adapter in adapter_map.get(state_code, []):
        field = adapter["canonical_field_name"]
        factor = float(adapter.get("unit_conversion_factor", 1.0))
        if field in result and isinstance(result[field], (int, float)) and factor != 1.0:
            result[field] = result[field] * factor
    return result


async def load_parcels(session, adapter_map: dict) -> None:
    for fname in ("chandigarh_parcels.geojson", "tn_village_parcels.geojson"):
        path = SEED_DIR / fname
        geojson = json.loads(path.read_text())
        for feature in geojson.get("features", []):
            props = dict(feature.get("properties", {}))
            geom = json.dumps(feature.get("geometry", {}))
            props = apply_conversions(props, adapter_map)
            record = {
                "ulpin": props.get("ulpin"),
                "state_code": props.get("state_code"),
                "district": props.get("district"),
                "tehsil": props.get("tehsil"),
                "village_or_city": props.get("village_or_city"),
                "geom": geom,
                "area_sqm": float(props.get("area_sqm", 0.0)),
                "survey_or_khasra_no": props.get("survey_or_khasra_no", ""),
                "source_system": props.get("source_system", ""),
                "last_synced_at": props.get("last_synced_at"),
            }
            if not record["ulpin"]:
                continue
            stmt = (
                pg_insert(Parcel)
                .values(**record)
                .on_conflict_do_update(index_elements=["ulpin"], set_=record)
            )
            await session.execute(stmt)


async def load_users(session) -> None:
    path = SEED_DIR / "users.json"
    users = json.loads(path.read_text())
    for u in users:
        plain = u.pop("password", u.pop("hashed_password", "password123"))
        u["hashed_password"] = hash_password(plain)
        stmt = pg_insert(User).values(**u).on_conflict_do_nothing()
        await session.execute(stmt)


async def load_simple(session, model, filename: str, adapter_map: dict) -> None:
    path = SEED_DIR / filename
    records = json.loads(path.read_text())
    for rec in records:
        rec = apply_conversions(rec, adapter_map)
        stmt = pg_insert(model).values(**rec).on_conflict_do_nothing()
        await session.execute(stmt)


async def main() -> None:
    async with SessionLocal() as session:
        async with session.begin():
            print("Loading state_adapter_config...")
            adapter_map = await load_state_adapter(session)
            print("Loading parcels...")
            await load_parcels(session, adapter_map)
            print("Loading users...")
            await load_users(session)
            print("Loading ror...")
            await load_simple(session, Ror, "ror.json", adapter_map)
            print("Loading registrations...")
            await load_simple(session, Registration, "registration.json", adapter_map)
            print("Loading encumbrances...")
            await load_simple(session, Encumbrance, "encumbrance.json", adapter_map)
            print("Loading zoning...")
            await load_simple(session, Zoning, "zoning.json", adapter_map)
            print("Loading building_permissions...")
            await load_simple(session, BuildingPermission, "building_permission.json", adapter_map)
            print("Loading tax...")
            await load_simple(session, Tax, "tax.json", adapter_map)
    print("✅ Seed data loaded.")


if __name__ == "__main__":
    asyncio.run(main())
