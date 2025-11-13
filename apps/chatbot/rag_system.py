from typing import List, Tuple, Optional, Dict, Any
import os
import logging
from .document_processor import DocumentProcessor
from .vector_store import VectorStore
from .ai_generator import AIGenerator
from .session_manager import SessionManager
from .search_tools import ToolManager, DocumentSearchTool, DocumentListTool
from .metadata_manager import MetadataManager
from .cache_manager import QueryResultCache
from .models import BusinessDocument, DocumentChunk

class RAGSystem:
    """Main orchestrator for the Retrieval-Augmented Generation system"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.document_processor = DocumentProcessor(config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        self.vector_store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
        self.ai_generator = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)
        self.session_manager = SessionManager(config.MAX_HISTORY)
        self.metadata_manager = MetadataManager(config.METADATA_CSV_PATH)
        self.query_cache = QueryResultCache(config.CACHE_TTL_MINUTES)
        
        # Initialize search tools with cache support
        self.tool_manager = ToolManager()
        self.document_search_tool = DocumentSearchTool(self.vector_store, self.query_cache)
        self.document_list_tool = DocumentListTool(self.vector_store)
        self.tool_manager.register_tool(self.document_search_tool)
        self.tool_manager.register_tool(self.document_list_tool)
        
        self.logger.info(f"RAG System initialized - Vector store: {config.CHROMA_PATH}, Model: {config.ANTHROPIC_MODEL}")
    
    def add_business_document(self, file_path: str) -> Tuple[BusinessDocument, int]:
        """
        Add a single business document to the knowledge base with metadata support.
        
        Args:
            file_path: Path to the business document
            
        Returns:
            Tuple of (BusinessDocument object, number of chunks created)
        """
        try:
            self.logger.info(f"Processing document: {file_path}")
            
            # Get metadata for this document
            doc_metadata = self.metadata_manager.get_metadata_for_file(file_path)
            self.logger.debug(f"Retrieved metadata for {file_path}: {doc_metadata.doc_type if doc_metadata else 'None'}")
            
            # Check for duplicate documents using content hash
            document, document_chunks = self.document_processor.process_business_document(file_path, doc_metadata)
            self.logger.debug(f"Document processed - {len(document_chunks)} chunks created")
            
            # Check if this document already exists (by content hash)
            if self.vector_store.document_exists(document.content_hash):
                self.logger.info(f"Document {document.title} already exists (duplicate content detected), skipping...")
                return document, 0
            
            # Add document metadata to vector store for semantic search
            self.vector_store.add_document_metadata(document)
            
            # Add document content chunks to vector store
            self.vector_store.add_document_content(document_chunks)
            
            self.logger.info(f"Successfully added {document.title} ({document.doc_type.value}) with {len(document_chunks)} chunks")
            return document, len(document_chunks)
        except Exception as e:
            self.logger.error(f"Error processing business document {file_path}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to process document {file_path}: {str(e)}") from e
    
    def add_document_folder(self, folder_path: str, clear_existing: bool = False) -> Tuple[int, int]:
        """
        Add all business documents from a folder.
        
        Args:
            folder_path: Path to folder containing business documents
            clear_existing: Whether to clear existing data first
            
        Returns:
            Tuple of (total documents added, total chunks created)
        """
        total_documents = 0
        total_chunks = 0
        
        # Clear existing data if requested
        if clear_existing:
            self.logger.warning("Clearing existing data for fresh rebuild...")
            self.vector_store.clear_all_data()
        
        if not os.path.exists(folder_path):
            self.logger.error(f"Folder {folder_path} does not exist")
            raise FileNotFoundError(f"Folder {folder_path} does not exist")
        
        # Get existing document titles to avoid re-processing
        existing_document_titles = set(self.vector_store.get_existing_document_titles())
        
        # Process each file in the folder (now supporting Excel/CSV)
        supported_extensions = ('.pdf', '.docx', '.txt', '.xlsx', '.xls', '.csv')
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path) and file_name.lower().endswith(supported_extensions):
                try:
                    # Use the enhanced add_business_document method
                    document, chunks_added = self.add_business_document(file_path)
                    
                    if document and chunks_added > 0:
                        total_documents += 1
                        total_chunks += chunks_added
                        existing_document_titles.add(document.title)
                except Exception as e:
                    self.logger.error(f"Error processing {file_name}: {e}", exc_info=True)
        
        return total_documents, total_chunks
    
    def query(self, query: str, session_id: Optional[str] = None) -> Tuple[str, List[str]]:
        """
        Process a user query using the RAG system with tool-based search.
        
        Args:
            query: User's question
            session_id: Optional session ID for conversation context
            
        Returns:
            Tuple of (response, sources list - empty for tool-based approach)
        """
        response = None
        sources = []
        
        try:
            # Create prompt for the AI with clear instructions for business documents
            prompt = f"""You are a helpful assistant for a small business LLC. Answer this question about the business documents, accounting, tax matters, or general business operations: {query}"""
            
            # Get conversation history if session exists
            history = None
            if session_id:
                history = self.session_manager.get_conversation_history(session_id)
            
            # Generate response using AI with tools
            response = self.ai_generator.generate_response(
                query=prompt,
                conversation_history=history,
                tools=self.tool_manager.get_tool_definitions(),
                tool_manager=self.tool_manager
            )
            
            # Update conversation history
            if session_id:
                self.session_manager.add_exchange(session_id, query, response)
            
        finally:
            # Always get and reset sources after retrieving them, even if an error occurred
            sources = self.tool_manager.get_last_sources()
            self.tool_manager.reset_sources()
        
        # Return response with sources from tool searches
        return response, sources
    
    def get_document_analytics(self) -> Dict:
        """Get analytics about the business document catalog"""
        all_titles = self.vector_store.get_existing_document_titles()
        # Filter out test files
        filtered_titles = [title for title in all_titles if not self._is_test_file(title)]
        return {
            "total_documents": len(filtered_titles),
            "document_titles": filtered_titles,
            "cache_stats": self.query_cache.get_stats()
        }
    
    def _is_test_file(self, filename: str) -> bool:
        """Check if a filename indicates a test file"""
        filename_lower = filename.lower()
        test_indicators = [
            'test_', 'sample_', '_test', '_sample',
            'test.', 'sample.', 'demo_', '_demo'
        ]
        return any(indicator in filename_lower for indicator in test_indicators)
    
    def clear_cache(self):
        """Clear the query result cache"""
        self.query_cache.clear()
    
    def get_cache_info(self) -> str:
        """Get formatted cache information"""
        return self.query_cache.get_cache_info()