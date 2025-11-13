"""
Database module for Poolula Platform

Contains:
- SQLModel models (Property, Transaction, Document, Obligation, AuditLog)
- Database connection management
- Enums and constants
- Alembic migrations

Design principles:
- Every entity has embedded provenance (JSON column)
- All mutations trigger audit log entries
- UUIDs for primary keys (better for distributed systems)
- Timestamps track creation and updates
"""

__all__ = [
    "TransactionCategory",
    "Property",
    "Transaction",
    "Document",
    "Obligation",
    "AuditLog",
]
