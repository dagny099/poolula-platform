"""
Database Query Tool for AI Assistant

Provides safe, read-only SQL query capabilities for the chatbot.

Features:
- SELECT-only queries (no mutations)
- Parameterized queries (SQL injection safe)
- Access to Property, Transaction, Document, Obligation tables
- Returns structured data with metadata
- Integrated with tool management system

Author: Poolula Platform
Date: 2025-11-13
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime
from decimal import Decimal
import json

from sqlmodel import Session, select, text
from sqlalchemy.exc import SQLAlchemyError

from core.database.connection import get_engine
from core.database.models import Property, Transaction, Document, Obligation
from core.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseQueryTool:
    """
    Safe database query tool for AI assistant

    Provides read-only access to business data with safety guarantees:
    - No INSERT, UPDATE, DELETE allowed
    - Parameterized queries only
    - Result size limits
    - Error handling with helpful messages
    """

    def __init__(self, max_results: int = 100):
        """
        Initialize database query tool

        Args:
            max_results: Maximum number of results to return (prevents large queries)
        """
        self.max_results = max_results
        self.engine = get_engine()

    def query_properties(
        self,
        status: Optional[str] = None,
        min_basis: Optional[float] = None,
        max_basis: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Query properties with filters

        Args:
            status: Filter by status (ACTIVE, SOLD, etc.)
            min_basis: Minimum total basis
            max_basis: Maximum total basis

        Returns:
            Dictionary with properties and metadata

        Example:
            >>> tool = DatabaseQueryTool()
            >>> result = tool.query_properties(status="ACTIVE")
            >>> print(f"Found {result['count']} active properties")
        """
        try:
            with Session(self.engine) as session:
                query = select(Property)

                # Apply filters
                if status:
                    query = query.where(Property.status == status)

                # Execute query
                properties = session.exec(query).all()

                # Apply post-query filters (calculated fields)
                if min_basis is not None or max_basis is not None:
                    properties = [
                        p for p in properties
                        if (min_basis is None or p.total_basis >= Decimal(str(min_basis)))
                        and (max_basis is None or p.total_basis <= Decimal(str(max_basis)))
                    ]

                # Limit results
                properties = properties[:self.max_results]

                # Serialize to dict
                properties_data = [self._serialize_property(p) for p in properties]

                return {
                    "success": True,
                    "count": len(properties_data),
                    "properties": properties_data,
                    "query": "query_properties",
                    "filters": {"status": status, "min_basis": min_basis, "max_basis": max_basis}
                }

        except Exception as e:
            logger.error(f"Error querying properties: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": "query_properties"
            }

    def query_transactions(
        self,
        property_id: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        transaction_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query transactions with filters

        Args:
            property_id: Filter by property UUID
            category: Filter by transaction category (RENTAL_INCOME, UTILITIES_GAS, etc.)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            min_amount: Minimum transaction amount
            max_amount: Maximum transaction amount
            transaction_type: Filter by type (REVENUE, EXPENSE, etc.)

        Returns:
            Dictionary with transactions and metadata
        """
        try:
            with Session(self.engine) as session:
                query = select(Transaction)

                # Apply filters
                if property_id:
                    query = query.where(Transaction.property_id == property_id)
                if category:
                    query = query.where(Transaction.category == category)
                if start_date:
                    query = query.where(Transaction.transaction_date >= date.fromisoformat(start_date))
                if end_date:
                    query = query.where(Transaction.transaction_date <= date.fromisoformat(end_date))
                if min_amount is not None:
                    query = query.where(Transaction.amount >= Decimal(str(min_amount)))
                if max_amount is not None:
                    query = query.where(Transaction.amount <= Decimal(str(max_amount)))
                if transaction_type:
                    query = query.where(Transaction.transaction_type == transaction_type)

                # Order by date (most recent first)
                query = query.order_by(Transaction.transaction_date.desc())

                # Execute and limit
                transactions = session.exec(query).all()[:self.max_results]

                # Serialize
                transactions_data = [self._serialize_transaction(t) for t in transactions]

                # Calculate summary stats
                total_amount = sum(Decimal(t["amount"]) for t in transactions_data)

                return {
                    "success": True,
                    "count": len(transactions_data),
                    "transactions": transactions_data,
                    "summary": {
                        "total_amount": str(total_amount),
                        "count": len(transactions_data)
                    },
                    "query": "query_transactions",
                    "filters": {
                        "property_id": property_id,
                        "category": category,
                        "start_date": start_date,
                        "end_date": end_date,
                        "transaction_type": transaction_type
                    }
                }

        except Exception as e:
            logger.error(f"Error querying transactions: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": "query_transactions"
            }

    def aggregate_transactions(
        self,
        group_by: str = "category",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        transaction_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate transactions by category, month, or type

        Args:
            group_by: How to group (category, month, type)
            start_date: Start date filter
            end_date: End date filter
            transaction_type: Filter by type

        Returns:
            Aggregated results with totals
        """
        try:
            with Session(self.engine) as session:
                query = select(Transaction)

                # Apply filters
                if start_date:
                    query = query.where(Transaction.transaction_date >= date.fromisoformat(start_date))
                if end_date:
                    query = query.where(Transaction.transaction_date <= date.fromisoformat(end_date))
                if transaction_type:
                    query = query.where(Transaction.transaction_type == transaction_type)

                transactions = session.exec(query).all()

                # Group and aggregate
                aggregated = {}

                for t in transactions:
                    if group_by == "category":
                        key = t.category
                    elif group_by == "month":
                        key = t.transaction_date.strftime("%Y-%m")
                    elif group_by == "type":
                        key = t.transaction_type
                    else:
                        key = "all"

                    if key not in aggregated:
                        aggregated[key] = {
                            "count": 0,
                            "total": Decimal("0.00")
                        }

                    aggregated[key]["count"] += 1
                    aggregated[key]["total"] += t.amount

                # Convert to list and serialize
                results = [
                    {
                        group_by: k,
                        "count": v["count"],
                        "total": str(v["total"])
                    }
                    for k, v in aggregated.items()
                ]

                # Sort by total (descending)
                results.sort(key=lambda x: Decimal(x["total"]), reverse=True)

                return {
                    "success": True,
                    "count": len(results),
                    "aggregated": results,
                    "group_by": group_by,
                    "query": "aggregate_transactions"
                }

        except Exception as e:
            logger.error(f"Error aggregating transactions: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": "aggregate_transactions"
            }

    def query_documents(
        self,
        property_id: Optional[str] = None,
        doc_type: Optional[str] = None,
        search_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query documents with filters

        Args:
            property_id: Filter by property UUID
            doc_type: Filter by document type
            search_filename: Search in filename (case-insensitive)

        Returns:
            Dictionary with documents and metadata
        """
        try:
            with Session(self.engine) as session:
                query = select(Document)

                # Apply filters
                if property_id:
                    query = query.where(Document.property_id == property_id)
                if doc_type:
                    query = query.where(Document.doc_type == doc_type)
                if search_filename:
                    query = query.where(Document.filename.ilike(f"%{search_filename}%"))

                # Execute and limit
                documents = session.exec(query).all()[:self.max_results]

                # Serialize
                documents_data = [self._serialize_document(d) for d in documents]

                return {
                    "success": True,
                    "count": len(documents_data),
                    "documents": documents_data,
                    "query": "query_documents"
                }

        except Exception as e:
            logger.error(f"Error querying documents: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": "query_documents"
            }

    def query_obligations(
        self,
        property_id: Optional[str] = None,
        status: Optional[str] = None,
        due_before: Optional[str] = None,
        due_after: Optional[str] = None,
        obligation_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query obligations with filters

        Args:
            property_id: Filter by property UUID
            status: Filter by status (PENDING, COMPLETED, etc.)
            due_before: Due before date (YYYY-MM-DD)
            due_after: Due after date (YYYY-MM-DD)
            obligation_type: Filter by type

        Returns:
            Dictionary with obligations and metadata
        """
        try:
            with Session(self.engine) as session:
                query = select(Obligation)

                # Apply filters
                if property_id:
                    query = query.where(Obligation.property_id == property_id)
                if status:
                    query = query.where(Obligation.status == status)
                if due_before:
                    query = query.where(Obligation.due_date <= date.fromisoformat(due_before))
                if due_after:
                    query = query.where(Obligation.due_date >= date.fromisoformat(due_after))
                if obligation_type:
                    query = query.where(Obligation.obligation_type == obligation_type)

                # Order by due date
                query = query.order_by(Obligation.due_date.asc())

                # Execute and limit
                obligations = session.exec(query).all()[:self.max_results]

                # Serialize
                obligations_data = [self._serialize_obligation(o) for o in obligations]

                return {
                    "success": True,
                    "count": len(obligations_data),
                    "obligations": obligations_data,
                    "query": "query_obligations"
                }

        except Exception as e:
            logger.error(f"Error querying obligations: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "query": "query_obligations"
            }

    # Serialization helpers

    def _serialize_property(self, property_obj: Property) -> Dict[str, Any]:
        """Convert Property to JSON-serializable dict"""
        return {
            "id": str(property_obj.id),
            "address": property_obj.address,
            "acquisition_date": property_obj.acquisition_date.isoformat(),
            "purchase_price_total": str(property_obj.purchase_price_total),
            "land_basis": str(property_obj.land_basis),
            "building_basis": str(property_obj.building_basis),
            "ffe_basis": str(property_obj.ffe_basis),
            "total_basis": str(property_obj.total_basis),
            "depreciable_basis": str(property_obj.depreciable_basis),
            "placed_in_service": property_obj.placed_in_service.isoformat() if property_obj.placed_in_service else None,
            "status": property_obj.status
        }

    def _serialize_transaction(self, transaction: Transaction) -> Dict[str, Any]:
        """Convert Transaction to JSON-serializable dict"""
        return {
            "id": str(transaction.id),
            "property_id": str(transaction.property_id),
            "transaction_date": transaction.transaction_date.isoformat(),
            "amount": str(transaction.amount),
            "category": transaction.category,
            "transaction_type": transaction.transaction_type,
            "description": transaction.description,
            "source_account": transaction.source_account
        }

    def _serialize_document(self, document: Document) -> Dict[str, Any]:
        """Convert Document to JSON-serializable dict"""
        return {
            "id": str(document.id),
            "property_id": str(document.property_id) if document.property_id else None,
            "filename": document.filename,
            "doc_type": document.doc_type,
            "effective_date": document.effective_date.isoformat() if document.effective_date else None,
            "version": document.version,
            "confidentiality": document.confidentiality
        }

    def _serialize_obligation(self, obligation: Obligation) -> Dict[str, Any]:
        """Convert Obligation to JSON-serializable dict"""
        return {
            "id": str(obligation.id),
            "property_id": str(obligation.property_id) if obligation.property_id else None,
            "obligation_type": obligation.obligation_type,
            "due_date": obligation.due_date.isoformat(),
            "status": obligation.status,
            "description": obligation.description,
            "is_overdue": obligation.is_overdue,
            "days_until_due": obligation.days_until_due
        }


# Tool definition for AI assistant
def get_database_tool_definition() -> Dict[str, Any]:
    """
    Get tool definition for AI assistant

    Returns:
        Tool definition in Claude API format
    """
    return {
        "name": "query_database",
        "description": "Query the business database for properties, transactions, documents, and obligations. Use this to answer questions about financial data, property information, and compliance obligations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["properties", "transactions", "aggregate_transactions", "documents", "obligations"],
                    "description": "Type of query to execute"
                },
                "filters": {
                    "type": "object",
                    "description": "Filters to apply to the query",
                    "properties": {
                        "property_id": {"type": "string"},
                        "status": {"type": "string"},
                        "category": {"type": "string"},
                        "transaction_type": {"type": "string"},
                        "start_date": {"type": "string", "description": "YYYY-MM-DD format"},
                        "end_date": {"type": "string", "description": "YYYY-MM-DD format"},
                        "min_amount": {"type": "number"},
                        "max_amount": {"type": "number"},
                        "doc_type": {"type": "string"},
                        "search_filename": {"type": "string"},
                        "obligation_type": {"type": "string"},
                        "due_before": {"type": "string"},
                        "due_after": {"type": "string"},
                        "group_by": {"type": "string", "enum": ["category", "month", "type"]}
                    }
                }
            },
            "required": ["query_type"]
        }
    }


def execute_database_query(query_type: str, filters: Optional[Dict[str, Any]] = None) -> str:
    """
    Execute a database query (called by AI tool manager)

    Args:
        query_type: Type of query (properties, transactions, etc.)
        filters: Optional filters for the query

    Returns:
        JSON string with query results
    """
    tool = DatabaseQueryTool()
    filters = filters or {}

    if query_type == "properties":
        result = tool.query_properties(**filters)
    elif query_type == "transactions":
        result = tool.query_transactions(**filters)
    elif query_type == "aggregate_transactions":
        result = tool.aggregate_transactions(**filters)
    elif query_type == "documents":
        result = tool.query_documents(**filters)
    elif query_type == "obligations":
        result = tool.query_obligations(**filters)
    else:
        result = {
            "success": False,
            "error": f"Unknown query type: {query_type}"
        }

    return json.dumps(result, indent=2)
