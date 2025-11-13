import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

from .config import config
from .rag_system import RAGSystem
from .health_check import HealthChecker, create_health_endpoint

# Note: DocumentIngestor will be moved to scripts/ directory
# For now, we'll handle document ingestion through the RAG system directly

# Initialize FastAPI app
app = FastAPI(
    title="Poolula Business Assistant",
    description="AI-powered business assistant for Poolula LLC compliance and document management",
    version="1.0.0",
    root_path=""
)

# Setup logging
logger = logging.getLogger(__name__)

# Add trusted host middleware for proxy
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Enable CORS with proper settings for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize RAG system
rag_system = RAGSystem(config)

# Note: DocumentIngestor removed - using rag_system.add_business_document directly

# Initialize health checker
health_checker = HealthChecker(config)
health_endpoint = create_health_endpoint(health_checker)

# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for business queries"""
    query: str
    session_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What is the operating agreement effective date?",
                "session_id": "uuid-string-optional"
            }
        }

class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[Dict[str, Any]]
    session_id: str

class DocumentStats(BaseModel):
    """Response model for document statistics"""
    total_documents: int
    document_titles: List[str]

class IncomingFilesResponse(BaseModel):
    """Response model for incoming files"""
    files: List[str]
    count: int

class ProcessingResponse(BaseModel):
    """Response model for processing operations"""
    success: bool
    message: str
    processed_files: List[str]
    failed_files: List[str]

class UploadResponse(BaseModel):
    """Response model for file upload"""
    success: bool
    message: str
    filename: str

# API Endpoints

@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Process a query and return response with sources"""
    try:
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()
        
        # Process query using RAG system
        answer, sources = rag_system.query(request.query, session_id)
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents", response_model=DocumentStats)
async def get_document_stats():
    """Get document analytics and statistics"""
    try:
        analytics = rag_system.get_document_analytics()
        return DocumentStats(
            total_documents=analytics["total_documents"],
            document_titles=analytics["document_titles"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incoming-files", response_model=IncomingFilesResponse)
async def get_incoming_files():
    """Get list of files in the incoming folder"""
    try:
        incoming_folder = Path("../docs/incoming")
        if not incoming_folder.exists():
            incoming_folder.mkdir(parents=True, exist_ok=True)
        
        # Get all files (not directories) from incoming folder
        files = []
        for file_path in incoming_folder.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                files.append(file_path.name)
        
        return IncomingFilesResponse(
            files=sorted(files),
            count=len(files)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to the incoming folder"""
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.docx', '.txt', '.md', '.csv', '.xlsx', '.xls'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Ensure incoming folder exists
        incoming_folder = Path("../docs/incoming")
        incoming_folder.mkdir(parents=True, exist_ok=True)
        
        # Save file to incoming folder
        file_path = incoming_folder / file.filename
        
        # Check if file already exists
        if file_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' already exists in incoming folder"
            )
        
        # Write the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return UploadResponse(
            success=True,
            message=f"File '{file.filename}' uploaded successfully",
            filename=file.filename
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-incoming", response_model=ProcessingResponse)
async def process_incoming_files():
    """Process all files in the incoming folder"""
    try:
        incoming_folder = Path("../docs/incoming")
        if not incoming_folder.exists():
            return ProcessingResponse(
                success=True,
                message="No incoming folder found, nothing to process",
                processed_files=[],
                failed_files=[]
            )
        
        # Get all files to process
        files_to_process = []
        for file_path in incoming_folder.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                files_to_process.append(file_path)
        
        if not files_to_process:
            return ProcessingResponse(
                success=True,
                message="No files found in incoming folder",
                processed_files=[],
                failed_files=[]
            )
        
        # Process each file
        processed_files = []
        failed_files = []

        for file_path in files_to_process:
            try:
                # Use rag_system directly to add documents
                document, chunks = rag_system.add_business_document(str(file_path))
                if document and chunks > 0:
                    processed_files.append(file_path.name)
                    # Move to processed folder
                    processed_folder = incoming_folder.parent / "processed"
                    processed_folder.mkdir(exist_ok=True)
                    file_path.rename(processed_folder / file_path.name)
                else:
                    failed_files.append(file_path.name)
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
                failed_files.append(file_path.name)
        
        # Return results
        total_files = len(files_to_process)
        success_count = len(processed_files)
        
        message = f"Processed {success_count}/{total_files} files successfully"
        if failed_files:
            message += f". Failed: {', '.join(failed_files)}"
        
        return ProcessingResponse(
            success=len(failed_files) == 0,
            message=message,
            processed_files=processed_files,
            failed_files=failed_files
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/incoming-files/{filename}")
async def delete_incoming_file(filename: str):
    """Delete a specific file from the incoming folder"""
    try:
        incoming_folder = Path("../docs/incoming")
        file_path = incoming_folder / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail=f"'{filename}' is not a file")
        
        file_path.unlink()
        return {"success": True, "message": f"File '{filename}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents/{filename:path}")
async def serve_document(filename: str):
    """Serve document files for preview/download"""
    try:
        # Check multiple possible locations for the document
        possible_paths = [
            Path("../docs") / filename,
            Path("../docs/processed") / filename,
            Path("../docs/incoming") / filename
        ]
        
        # Find the file in one of the possible locations
        file_path = None
        for path in possible_paths:
            if path.exists() and path.is_file():
                file_path = path
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        # Get file extension to set proper content type
        extension = file_path.suffix.lower()
        content_type_map = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel'
        }
        
        content_type = content_type_map.get(extension, 'application/octet-stream')
        
        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup"""
    docs_path = "../docs"
    if os.path.exists(docs_path):
        print("Loading initial documents...")
        try:
            documents, chunks = rag_system.add_document_folder(docs_path, clear_existing=False)
            print(f"Loaded {documents} documents with {chunks} chunks")
        except Exception as e:
            print(f"Error loading documents: {e}")

# Custom static file handler with no-cache headers for development
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            # Add no-cache headers for development
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
    
    
# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """System health check endpoint for monitoring"""
    return health_endpoint()

# Serve static files for the frontend
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")