"""
conftest.py — pytest configuration and shared fixtures for backend/tests/.

Patches GeoAlchemy2's DDL helper to be compatible with SQLAlchemy 2.1+, which
made ``ColumnCollection`` an abstract base class.  GeoAlchemy2 0.15.x calls
``expression.ColumnCollection()`` directly in its ``before_create`` handler;
this crashes when any test creates an in-memory SQLite table after a test that
loaded the full app (which registers GeoAlchemy2's global Table event hooks).

The fix replaces the call with ``WriteableColumnCollection()``, which is the
concrete subclass SQLAlchemy 2.1 expects.  This patch is applied once at
session start and is completely transparent to the tests.
"""

from __future__ import annotations

import geoalchemy2.admin.dialects.common as _ga2_common
from sqlalchemy.sql import expression as _expr


def _patched_update_table_for_dispatch(table, regular_cols):
    """Drop-in replacement that uses WriteableColumnCollection (SQLAlchemy 2.1+)."""
    table.info["_saved_columns"] = table.columns
    column_collection = _expr.WriteableColumnCollection()
    for col in regular_cols:
        column_collection.add(col)
    table.columns = column_collection


# Apply the patch immediately at import time (session scope).
_ga2_common._update_table_for_dispatch = _patched_update_table_for_dispatch
