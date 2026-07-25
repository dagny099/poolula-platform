"""
Shared helpers for API route modules

Keeps enum parsing and audit logging consistent across resources without
introducing a service/repository layer.
"""

from typing import Any, Optional, Type, TypeVar
from enum import Enum

from fastapi import HTTPException
from sqlmodel import Session, SQLModel

from core.database.models import AuditLog

E = TypeVar("E", bound=Enum)


def parse_enum(enum_cls: Type[E], value: Any, field_name: str) -> E:
    """
    Parse a string into an enum, accepting both the enum name (UTILITIES_GAS)
    and the enum value (utilities:gas). Raises HTTP 422 on failure.
    """
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls[value.upper()]
        except KeyError:
            try:
                return enum_cls(value.lower())
            except ValueError:
                pass
    valid = ", ".join(e.value for e in enum_cls)
    raise HTTPException(
        status_code=422,
        detail=f"Invalid {field_name}: {value}. Must be one of: {valid}",
    )


def parse_enum_for_validator(enum_cls: Type[E], value: Any) -> Any:
    """
    Enum parser for use inside Pydantic field validators.

    Accepts enum name or value; returns the raw input unchanged when it cannot
    be parsed so Pydantic produces a normal 422 validation error.
    """
    if value is None or isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls[value.upper()]
        except KeyError:
            try:
                return enum_cls(value.lower())
            except ValueError:
                pass
    return value


def record_audit(
    session: Session,
    action: str,
    entity: SQLModel,
    reason: str,
    old_value: Optional[dict] = None,
    user: str = "api",
) -> None:
    """
    Append an entry to the immutable audit log for a data mutation.

    Adds the entry to the session; caller commits (so the audit row and the
    mutation share one transaction).
    """
    audit = AuditLog(
        user=user,
        action=action,
        entity_type=type(entity).__name__,
        entity_id=entity.id,
        old_value=old_value,
        new_value=entity.model_dump(mode="json") if action != "DELETE" else None,
        reason=reason,
        context={"source": "rest_api"},
    )
    session.add(audit)
