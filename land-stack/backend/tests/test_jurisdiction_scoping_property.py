"""
Property 6: Jurisdiction scoping -- Validates Requirements 5.4, 5.5

For any officer JWT with a random jurisdiction value, and for any parcel whose
state_code != jurisdiction, all write endpoints return 403.
"""

from __future__ import annotations
import sys, os
_b = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _b not in sys.path: sys.path.insert(0, _b)
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
import httpx, pytest
from hypothesis import given, settings, strategies as st
from core.auth import create_access_token

S = ["MH", "TN", "PB", "DL", "KA"]

def _t(r, j=None): return create_access_token({"sub": f"u_{r.lower()}", "role": r, "jurisdiction": j})
def _h(r, j=None): return {"Authorization": f"Bearer {_t(r, j)}"}
def _dbo(m):
    async def _o(): yield m
    return _o
def _rm():
    r = AsyncMock(); r.exists = AsyncMock(return_value=0); r.publish = AsyncMock(return_value=1); return r

class _FR:
    def __init__(s, u="MH-MUM-001"):
        s.ulpin = u; s.owner_name = "Ramesh Kumar"; s.tenure_type = "Freehold"
        s.khatauni_no = "K/42"; s.land_use_type = "Residential"; s.mutation_status = "Clear"
        s.last_updated = date(2024, 1, 15)

def _jdb(r, ps):
    d = AsyncMock(); c = [0]
    async def _e(stmt, *a, **k):
        c[0] += 1; res = MagicMock()
        if c[0] == 1: res.scalar_one_or_none.return_value = ps
        else: res.scalar_one_or_none.return_value = r
        return res
    d.execute = AsyncMock(side_effect=_e); d.flush = AsyncMock(); d.commit = AsyncMock(); d.add = MagicMock()
    return d

@given(jurisdiction=st.sampled_from(S), parcel_state=st.sampled_from(S))
@settings(max_examples=50, deadline=None)
@pytest.mark.anyio
async def test_jurisdiction_mismatch_blocks_write(anyio_backend, jurisdiction, parcel_state):
    if jurisdiction == parcel_state: return
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis
    r = _FR(); d = _jdb(r, parcel_state); rm = _rm()
    app.dependency_overrides[get_db] = _dbo(d)
    app.dependency_overrides[get_redis] = lambda: rm
    try:
        with patch("routers.ror.write_audit", new_callable=AsyncMock):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.put(f"/api/v1/ror/{r.ulpin}", json={"mutation_status": "Pending"}, headers=_h("REV_OFF", jurisdiction))
    finally: app.dependency_overrides.clear()
    assert resp.status_code == 403

@given(state=st.sampled_from(S))
@settings(max_examples=20, deadline=None)
@pytest.mark.anyio
async def test_jurisdiction_match_allows_write(anyio_backend, state):
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis
    r = _FR(); d = _jdb(r, state); rm = _rm()
    app.dependency_overrides[get_db] = _dbo(d)
    app.dependency_overrides[get_redis] = lambda: rm
    try:
        with patch("routers.ror.write_audit", new_callable=AsyncMock):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.put(f"/api/v1/ror/{r.ulpin}", json={"mutation_status": "Pending"}, headers=_h("REV_OFF", state))
    finally: app.dependency_overrides.clear()
    assert resp.status_code == 200
