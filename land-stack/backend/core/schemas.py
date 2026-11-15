"""
core/schemas.py — Shared Pydantic envelope and error models.

Every router in Land Stack returns Envelope[T] via the ok() or err() helpers.
Response shape (success):  {"success": true,  "data": {...}, "errors": []}
Response shape (error):    {"success": false, "data": null,  "errors": [{...}]}
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """A single structured error item carried inside an error envelope."""

    code: str
    message: str
    field: str | None = None


class Envelope(BaseModel, Generic[T]):
    """
    Standard response wrapper returned by every route.

    Fields
    ------
    success : bool
        True when the request was handled successfully; False on any error.
    data : T | None
        The response payload on success; None on error.
    errors : list[ErrorDetail]
        Empty list on success; one or more error details on failure.
    """

    success: bool
    data: T | None = None
    errors: list[ErrorDetail] = []


def ok(data: T) -> Envelope[T]:
    """Wrap a successful payload in an Envelope."""
    return Envelope(success=True, data=data, errors=[])


def err(
    code: str,
    message: str,
    field: str | None = None,
) -> Envelope[None]:
    """Wrap a single error in an Envelope."""
    return Envelope(
        success=False,
        data=None,
        errors=[ErrorDetail(code=code, message=message, field=field)],
    )
