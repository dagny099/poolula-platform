"""
Chat API endpoints for Poolula Platform

Provides chatbot query interface and document search via RAG system
"""

import os
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlmodel import Session

from apps.api import ingestion
from apps.chatbot.rag_system import RAGSystem
from apps.chatbot.config import Config
from apps.dspy.runtime import run_dspy_program
from core.database.connection import get_session
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
        # Create config (reads ANTHROPIC_API_KEY from environment)
        config = Config()
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")

        _rag_system = RAGSystem(config=config)
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

        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Try DSPy program if feature flag is enabled and artifact loads; fallback to baseline RAG.
        dspy_result = run_dspy_program(question=request.query, session_id=session_id)
        if dspy_result:
            response_text, sources_list = dspy_result
        else:
            rag = get_rag_system()
            response_text, sources_list = rag.query(
                query=request.query,
                session_id=session_id
            )

        # Format response for frontend
        return QueryResponse(
            answer=response_text,
            sources=sources_list,
            session_id=session_id
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
    files = ingestion.list_incoming_files()
    return {
        "count": len(files),
        "files": files,
    }


@router.post("/process-incoming")
async def process_incoming(session: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    Process files from incoming folder

    Chunks and embeds each pending file into the vector store, registers a
    Document row in the database (with provenance + audit log entry), and moves
    the file to the processed folder. Duplicate content (by SHA-256 hash) is
    skipped; failed files stay in the incoming folder for retry.

    Returns:
        Processing result with processed, skipped, and failed file lists

    Example:
        >>> POST /api/process-incoming
        >>> {
        >>>     "message": "Successfully processed 2 document(s)",
        >>>     "processed_files": ["document1.pdf", "document2.docx"],
        >>>     "skipped_files": [],
        >>>     "failed_files": []
        >>> }
    """
    try:
        return ingestion.process_incoming_files(session)
    except Exception as e:
        logger.error(f"Error processing incoming files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process incoming files: {str(e)}")


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload file to incoming folder

    Saves the file to the incoming folder for later processing via
    POST /api/process-incoming. Supported types: pdf, docx, txt, md,
    xlsx, xls, csv (max 50 MB). Name collisions get a numeric suffix.

    Returns:
        Upload confirmation with the stored filename

    Example:
        >>> POST /api/upload
        >>> (multipart/form-data with file)
        >>> {
        >>>     "message": "File uploaded successfully",
        >>>     "filename": "document.pdf"
        >>> }
    """
    stored_name = await ingestion.save_upload_file(file)
    return {
        "message": "File uploaded successfully",
        "filename": stored_name,
    }
