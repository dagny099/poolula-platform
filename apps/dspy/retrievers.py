"""
DSPy Retrievers for Poolula Platform

Wraps existing tools (DatabaseTool, VectorStore) as DSPy retrieval modules.
"""
import dspy
from typing import List, Optional, Dict, Any
from apps.chatbot.database_tool import DatabaseQueryTool
from apps.chatbot.vector_store import VectorStore
from apps.chatbot.config import Config


class DatabaseRetriever(dspy.Retrieve):
    """
    DSPy retriever that wraps DatabaseQueryTool.

    Translates natural language queries into structured database queries
    and returns results as passages.
    """

    def __init__(self, database_tool: Optional[DatabaseQueryTool] = None, k: int = 10):
        """
        Args:
            database_tool: DatabaseQueryTool instance (creates new if None)
            k: Maximum number of results to return
        """
        super().__init__(k=k)
        self.database_tool = database_tool or DatabaseQueryTool()

    def forward(self, query_or_queries: str | List[str], k: Optional[int] = None) -> dspy.Prediction:
        """
        Retrieve database results for query.

        Args:
            query_or_queries: Natural language query or list of queries
            k: Override default k value

        Returns:
            dspy.Prediction with passages field containing formatted results
        """
        k = k or self.k

        # Handle single query or list
        queries = [query_or_queries] if isinstance(query_or_queries, str) else query_or_queries

        all_passages = []

        for query in queries:
            # Simple heuristic to determine query type from natural language
            query_type, filters = self._parse_query(query)

            # Execute database query
            result = self._execute_query(query_type, filters, k)

            # Format as passages
            passages = self._format_result_as_passages(result, query_type)
            all_passages.extend(passages[:k])

        return dspy.Prediction(passages=all_passages)

    def _parse_query(self, query: str) -> tuple[str, Dict[str, Any]]:
        """
        Parse natural language query into query_type and filters.

        This is a simple heuristic parser. In production, you might use:
        - LLM-based query understanding
        - Intent classification model
        - Rule-based NLU
        """
        query_lower = query.lower()

        # Detect query type
        if any(word in query_lower for word in ["property", "properties", "address"]):
            query_type = "query_properties"
            filters = {}
        elif any(word in query_lower for word in ["transaction", "income", "expense", "rental"]):
            query_type = "query_transactions"
            filters = {}

            # Extract date if present (simple pattern matching)
            import re
            year_match = re.search(r'(202[0-9])', query)
            month_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)', query_lower)

            if year_match and month_match:
                year = year_match.group(1)
                month_map = {
                    "january": "01", "february": "02", "march": "03", "april": "04",
                    "may": "05", "june": "06", "july": "07", "august": "08",
                    "september": "09", "october": "10", "november": "11", "december": "12"
                }
                month = month_map.get(month_match.group(1))
                if month:
                    filters["start_date"] = f"{year}-{month}-01"
                    # Calculate last day of month
                    if month in ["01", "03", "05", "07", "08", "10", "12"]:
                        last_day = "31"
                    elif month in ["04", "06", "09", "11"]:
                        last_day = "30"
                    else:  # February
                        last_day = "29" if int(year) % 4 == 0 else "28"
                    filters["end_date"] = f"{year}-{month}-{last_day}"

        elif any(word in query_lower for word in ["document", "file", "pdf"]):
            query_type = "query_documents"
            filters = {}
        elif any(word in query_lower for word in ["obligation", "compliance", "deadline"]):
            query_type = "query_obligations"
            filters = {}
        else:
            # Default to transactions
            query_type = "query_transactions"
            filters = {}

        return query_type, filters

    def _execute_query(self, query_type: str, filters: Dict[str, Any], limit: int) -> Dict[str, Any]:
        """Execute the database query"""
        method = getattr(self.database_tool, query_type, None)
        if not method:
            return {"success": False, "error": f"Unknown query type: {query_type}"}

        try:
            return method(**filters)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_result_as_passages(self, result: Dict[str, Any], query_type: str) -> List[str]:
        """Format database results as text passages for DSPy"""
        if not result.get("success"):
            return [f"Database query failed: {result.get('error', 'Unknown error')}"]

        passages = []

        if query_type == "query_properties":
            for prop in result.get("properties", []):
                passage = (
                    f"Property: {prop.get('address', 'N/A')}\n"
                    f"Status: {prop.get('status', 'N/A')}\n"
                    f"Acquisition Date: {prop.get('acquisition_date', 'N/A')}\n"
                    f"Initial Basis: ${prop.get('initial_basis', 0):,.2f}"
                )
                passages.append(passage)

        elif query_type == "query_transactions":
            summary = result.get("summary", {})
            if summary:
                total_amount = summary.get('total_amount', 0)
                # Convert to float if it's a string
                if isinstance(total_amount, str):
                    try:
                        total_amount = float(total_amount)
                    except (ValueError, TypeError):
                        total_amount = 0
                passages.append(
                    f"Transaction Summary:\n"
                    f"Total Amount: ${total_amount:,.2f}\n"
                    f"Count: {summary.get('count', 0)}"
                )

            for txn in result.get("transactions", [])[:5]:  # Top 5
                amount = txn.get('amount', 0)
                # Convert to float if it's a string
                if isinstance(amount, str):
                    try:
                        amount = float(amount)
                    except (ValueError, TypeError):
                        amount = 0
                passage = (
                    f"Transaction: {txn.get('description', 'N/A')}\n"
                    f"Date: {txn.get('transaction_date', 'N/A')}\n"
                    f"Amount: ${amount:,.2f}\n"
                    f"Category: {txn.get('category', 'N/A')}"
                )
                passages.append(passage)

        elif query_type == "query_documents":
            for doc in result.get("documents", []):
                passage = (
                    f"Document: {doc.get('filename', 'N/A')}\n"
                    f"Type: {doc.get('doc_type', 'N/A')}\n"
                    f"Property: {doc.get('property_address', 'N/A')}"
                )
                passages.append(passage)

        elif query_type == "query_obligations":
            for obl in result.get("obligations", []):
                passage = (
                    f"Obligation: {obl.get('title', 'N/A')}\n"
                    f"Due Date: {obl.get('due_date', 'N/A')}\n"
                    f"Status: {obl.get('status', 'N/A')}"
                )
                passages.append(passage)

        return passages if passages else ["No results found"]


class VectorStoreRetriever(dspy.Retrieve):
    """
    DSPy retriever that wraps VectorStore for document search.
    """

    def __init__(self, vector_store: Optional[VectorStore] = None, k: int = 5):
        super().__init__(k=k)
        if vector_store:
            self.vector_store = vector_store
        else:
            config = Config()
            self.vector_store = VectorStore(
                chroma_path=config.CHROMA_PATH,
                embedding_model=config.EMBEDDING_MODEL,
                max_results=k
            )

    def forward(self, query_or_queries: str | List[str], k: Optional[int] = None) -> dspy.Prediction:
        """
        Retrieve documents via vector similarity search.

        Args:
            query_or_queries: Query or list of queries
            k: Number of results to return

        Returns:
            dspy.Prediction with passages field
        """
        k = k or self.k
        queries = [query_or_queries] if isinstance(query_or_queries, str) else query_or_queries

        all_passages = []

        for query in queries:
            # Call vector store search
            results = self.vector_store.search_documents_enhanced(
                query=query,
                limit=k
            )

            # Format as passages
            # results.documents is List[str], results.metadata is List[Dict]
            for i, doc_content in enumerate(results.documents):
                metadata = results.metadata[i] if i < len(results.metadata) else {}
                passage = (
                    f"[{metadata.get('document_title', 'Unknown')} - Page {metadata.get('page_number', 'N/A')}]\n"
                    f"{doc_content}"
                )
                all_passages.append(passage)

        return dspy.Prediction(passages=all_passages if all_passages else ["No documents found"])


class HybridRetriever(dspy.Retrieve):
    """
    Combined retriever that uses both database and vector search.
    """

    def __init__(self, database_tool=None, vector_store=None, k: int = 5):
        super().__init__(k=k)
        self.db_retriever = DatabaseRetriever(database_tool, k=k//2)
        self.vector_retriever = VectorStoreRetriever(vector_store, k=k//2)

    def forward(self, query_or_queries: str | List[str], k: Optional[int] = None) -> dspy.Prediction:
        """Retrieve from both database and documents"""
        k = k or self.k

        # Get results from both retrievers
        db_results = self.db_retriever(query_or_queries, k=k//2)
        vec_results = self.vector_retriever(query_or_queries, k=k//2)

        # Combine passages
        combined_passages = db_results.passages + vec_results.passages

        return dspy.Prediction(passages=combined_passages[:k])
