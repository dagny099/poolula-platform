"""
Audit Logging for Chatbot Q&A Exchanges

Logs all chatbot interactions to the database audit log for:
- Compliance tracking
- Quality monitoring
- Data lineage
- System debugging

Author: Poolula Platform
Date: 2025-11-13
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from sqlmodel import Session
from core.database.connection import get_engine
from core.database.models import AuditLog
from core.logging_config import get_logger

logger = get_logger(__name__)


class ChatbotAuditLogger:
    """
    Audit logger for chatbot Q&A exchanges

    Captures:
    - User queries and AI responses
    - Tools used during query processing
    - Sources referenced
    - Session context
    - Performance metrics
    """

    def __init__(self):
        self.engine = get_engine()

    def log_query_exchange(
        self,
        user_query: str,
        ai_response: str,
        session_id: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        response_time_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Log a complete Q&A exchange to the audit log

        Args:
            user_query: The user's original question
            ai_response: The AI's generated response
            session_id: Session identifier for conversation tracking
            tools_used: List of tool names that were invoked
            sources: List of source objects returned by tools
            response_time_ms: Query processing time in milliseconds
            error: Error message if query failed

        Example:
            >>> logger = ChatbotAuditLogger()
            >>> logger.log_query_exchange(
            ...     user_query="What is our total rental income?",
            ...     ai_response="Your total rental income is $5,200.",
            ...     tools_used=["query_database"],
            ...     response_time_ms=350.5
            ... )
        """
        try:
            with Session(self.engine) as session:
                # Build context dictionary with all metadata
                context = {
                    "session_id": session_id,
                    "query_length": len(user_query),
                    "response_length": len(ai_response),
                    "response_time_ms": response_time_ms,
                    "tools_used": tools_used or [],
                    "source_count": len(sources) if sources else 0,
                    "sources": sources or [],
                    "error": error,
                    "timestamp": datetime.utcnow().isoformat()
                }

                # Create audit log entry
                audit_entry = AuditLog(
                    user="ai:chatbot",  # System identifier
                    action="CHATBOT_QUERY",
                    entity_type="ChatbotExchange",
                    entity_id=uuid4(),  # Generate unique ID for this exchange
                    old_value={"query": user_query},  # Store user input
                    new_value={"response": ai_response},  # Store AI output
                    reason=f"User query: {user_query[:100]}{'...' if len(user_query) > 100 else ''}",
                    context=context
                )

                session.add(audit_entry)
                session.commit()

                logger.debug(f"Logged chatbot exchange - Session: {session_id}, Tools: {tools_used}")

        except Exception as e:
            # Don't fail the query if audit logging fails
            logger.error(f"Failed to log chatbot exchange: {e}", exc_info=True)

    def log_tool_execution(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: str,
        session_id: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Log individual tool execution for detailed tracking

        Args:
            tool_name: Name of the tool that was executed
            tool_input: Parameters passed to the tool
            tool_output: Result returned by the tool
            session_id: Session identifier
            execution_time_ms: Tool execution time in milliseconds
            error: Error message if tool execution failed
        """
        try:
            with Session(self.engine) as session:
                context = {
                    "session_id": session_id,
                    "execution_time_ms": execution_time_ms,
                    "error": error,
                    "input_parameters": tool_input,
                    "output_length": len(tool_output),
                    "timestamp": datetime.utcnow().isoformat()
                }

                audit_entry = AuditLog(
                    user="ai:chatbot",
                    action="TOOL_EXECUTION",
                    entity_type="ToolCall",
                    entity_id=uuid4(),
                    old_value={"tool_name": tool_name, "input": tool_input},
                    new_value={"output": tool_output[:500]},  # Truncate large outputs
                    reason=f"Tool execution: {tool_name}",
                    context=context
                )

                session.add(audit_entry)
                session.commit()

                logger.debug(f"Logged tool execution - Tool: {tool_name}, Session: {session_id}")

        except Exception as e:
            logger.error(f"Failed to log tool execution: {e}", exc_info=True)

    def get_recent_exchanges(
        self,
        limit: int = 10,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent chatbot exchanges from audit log

        Args:
            limit: Maximum number of exchanges to return
            session_id: Optional filter by session ID

        Returns:
            List of exchange dictionaries with query, response, and metadata
        """
        try:
            with Session(self.engine) as session:
                from sqlmodel import select

                query = select(AuditLog).where(
                    AuditLog.action == "CHATBOT_QUERY"
                ).order_by(AuditLog.timestamp.desc()).limit(limit)

                # Filter by session if provided
                if session_id:
                    query = query.where(
                        AuditLog.context["session_id"].astext == session_id
                    )

                results = session.exec(query).all()

                exchanges = []
                for entry in results:
                    exchanges.append({
                        "timestamp": entry.timestamp,
                        "query": entry.old_value.get("query"),
                        "response": entry.new_value.get("response"),
                        "session_id": entry.context.get("session_id"),
                        "tools_used": entry.context.get("tools_used", []),
                        "response_time_ms": entry.context.get("response_time_ms"),
                        "error": entry.context.get("error")
                    })

                return exchanges

        except Exception as e:
            logger.error(f"Failed to retrieve recent exchanges: {e}", exc_info=True)
            return []
