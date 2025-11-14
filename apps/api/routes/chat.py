"""
Chat API endpoints for Poolula Platform

Provides chatbot query interface and document search via RAG system
"""

import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.chatbot.rag_system import RAGSystem
from core.logging_config import get_logger

logger = get_logger(__name__)

# Initialize router
router = APIRouter()

# Initialize RAG system (singleton pattern)
_rag_system = None


def get_rag_system() -> RAGSystem:
    """Get or create RAG system instance"""
    global _rag_system
    if _rag_system is None:
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")

        _rag_system = RAGSystem(api_key=api_key)
        logger.info("RAG system initialized")

    return _rag_system


# Request/Response models
class QueryRequest(BaseModel):
    """Query request from frontend"""
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Query response to frontend"""
    answer: str
    sources: list
    session_id: str


class DocumentsResponse(BaseModel):
    """Documents list response"""
    total_documents: int
    document_titles: list[str]


# Endpoints

@router.post("/query")
async def query_chatbot(request: QueryRequest) -> QueryResponse:
    """
    Query the chatbot with natural language question

    Processes user query through RAG system with database and document search.

    Args:
        request: Query request with user question and optional session ID

    Returns:
        Response with AI answer, sources, and session ID

    Example:
        >>> POST /api/query
        >>> {
        >>>     "query": "What was my rental income in August 2025?",
        >>>     "session_id": null
        >>> }
        >>> Response:
        >>> {
        >>>     "answer": "Your rental income in August 2025 was $16,144.12...",
        >>>     "sources": [{...}],
        >>>     "session_id": "uuid-here"
        >>> }
    """
    try:
        logger.info(f"Query received: {request.query[:100]}...")

        # Get RAG system
        rag = get_rag_system()

        # Process query
        response = rag.query(
            query=request.query,
            session_id=request.session_id
        )

        # Format response for frontend
        return QueryResponse(
            answer=response.get("response", ""),
            sources=response.get("sources", []),
            session_id=response.get("session_id", "")
        )

    except Exception as e:
        logger.error(f"Query processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@router.get("/documents")
async def list_documents() -> DocumentsResponse:
    """
    List all ingested documents

    Returns count and titles of all documents in vector store.

    Returns:
        Response with document count and list of titles

    Example:
        >>> GET /api/documents
        >>> {
        >>>     "total_documents": 8,
        >>>     "document_titles": ["Articles of Organization", "Operating Agreement", ...]
        >>> }
    """
    try:
        # Get RAG system
        rag = get_rag_system()

        # Get document list from vector store
        titles = rag.vector_store.get_existing_document_titles()

        return DocumentsResponse(
            total_documents=len(titles),
            document_titles=titles
        )

    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/documents/{document_title}")
async def get_document(document_title: str) -> Dict[str, Any]:
    """
    Get document metadata by title

    Args:
        document_title: Document title to retrieve

    Returns:
        Document metadata

    Example:
        >>> GET /api/documents/Articles%20of%20Organization
        >>> {
        >>>     "title": "Articles of Organization",
        >>>     "doc_type": "formation",
        >>>     "effective_date": "2024-05-15",
        >>>     ...
        >>> }
    """
    try:
        # Get RAG system
        rag = get_rag_system()

        # Get document metadata
        metadata = rag.vector_store.get_document_by_title(document_title)

        if not metadata:
            raise HTTPException(status_code=404, detail=f"Document not found: {document_title}")

        return metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {str(e)}")


@router.get("/incoming-files")
async def check_incoming_files() -> Dict[str, Any]:
    """
    Check for files in incoming folder waiting to be processed

    Returns:
        Count and list of files in incoming folder

    Example:
        >>> GET /api/incoming-files
        >>> {
        >>>     "count": 2,
        >>>     "files": ["document1.pdf", "document2.docx"]
        >>> }
    """
    # TODO: Implement incoming files check
    # For now, return empty
    return {
        "count": 0,
        "files": []
    }


@router.post("/process-incoming")
async def process_incoming_files() -> Dict[str, Any]:
    """
    Process files from incoming folder

    Ingests documents from incoming folder into vector store.

    Returns:
        Processing result with count and file list

    Example:
        >>> POST /api/process-incoming
        >>> {
        >>>     "message": "Successfully processed 2 documents",
        >>>     "processed_files": ["document1.pdf", "document2.docx"]
        >>> }
    """
    # TODO: Implement incoming files processing
    # For now, return success with empty list
    return {
        "message": "No files to process",
        "processed_files": []
    }


@router.post("/upload")
async def upload_file() -> Dict[str, Any]:
    """
    Upload file to incoming folder

    Receives file upload and saves to incoming folder for processing.

    Returns:
        Upload confirmation

    Example:
        >>> POST /api/upload
        >>> (multipart/form-data with file)
        >>> {
        >>>     "message": "File uploaded successfully",
        >>>     "filename": "document.pdf"
        >>> }
    """
    # TODO: Implement file upload
    # For now, return not implemented
    raise HTTPException(status_code=501, detail="File upload not yet implemented")
