import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .models import BusinessDocument, DocumentChunk

# Define backward compatibility stubs for old course methods
class Course:
    def __init__(self, title="", course_link=None, instructor=None, lessons=None):
        self.title = title
        self.course_link = course_link
        self.instructor = instructor
        self.lessons = lessons or []

class CourseChunk:
    def __init__(self, content="", course_title="", lesson_number=None, chunk_index=0):
        self.content = content
        self.course_title = course_title
        self.lesson_number = lesson_number
        self.chunk_index = chunk_index

@dataclass
class SearchResults:
    """Container for search results with metadata"""
    documents: List[str]
    metadata: List[Dict[str, Any]]
    distances: List[float]
    error: Optional[str] = None
    
    @classmethod
    def from_chroma(cls, chroma_results: Dict) -> 'SearchResults':
        """Create SearchResults from ChromaDB query results"""
        return cls(
            documents=chroma_results['documents'][0] if chroma_results['documents'] else [],
            metadata=chroma_results['metadatas'][0] if chroma_results['metadatas'] else [],
            distances=chroma_results['distances'][0] if chroma_results['distances'] else []
        )
    
    @classmethod
    def empty(cls, error_msg: str) -> 'SearchResults':
        """Create empty results with error message"""
        return cls(documents=[], metadata=[], distances=[], error=error_msg)
    
    def is_empty(self) -> bool:
        """Check if results are empty"""
        return len(self.documents) == 0

class VectorStore:
    """Vector storage using ChromaDB for business document content and metadata"""
    
    def __init__(self, chroma_path: str, embedding_model: str, max_results: int = 5):
        self.max_results = max_results
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )

        # Use ChromaDB's default embedding function (ONNX-based, no torch required)
        # This provides a good balance of performance and compatibility
        self.embedding_function = chromadb.utils.embedding_functions.ONNXMiniLM_L6_V2()
        
        # Create collections for different types of data
        self.document_catalog = self._create_collection("document_catalog")  # Document titles/metadata
        self.document_content = self._create_collection("document_content")  # Actual document content
    
    def _create_collection(self, name: str):
        """Create or get a ChromaDB collection"""
        return self.client.get_or_create_collection(
            name=name,
            embedding_function=self.embedding_function
        )
    
    def search(self, 
               query: str,
               course_name: Optional[str] = None,
               lesson_number: Optional[int] = None,
               limit: Optional[int] = None) -> SearchResults:
        """
        Main search interface that handles course resolution and content search.
        
        Args:
            query: What to search for in course content
            course_name: Optional course name/title to filter by
            lesson_number: Optional lesson number to filter by
            limit: Maximum results to return
            
        Returns:
            SearchResults object with documents and metadata
        """
        # Step 1: Resolve course name if provided
        course_title = None
        if course_name:
            course_title = self._resolve_course_name(course_name)
            if not course_title:
                return SearchResults.empty(f"No course found matching '{course_name}'")
        
        # Step 2: Build filter for content search
        filter_dict = self._build_filter(course_title, lesson_number)
        
        # Step 3: Search course content
        # Use provided limit or fall back to configured max_results
        search_limit = limit if limit is not None else self.max_results
        
        try:
            results = self.course_content.query(
                query_texts=[query],
                n_results=search_limit,
                where=filter_dict
            )
            return SearchResults.from_chroma(results)
        except Exception as e:
            return SearchResults.empty(f"Search error: {str(e)}")
    
    def _resolve_course_name(self, course_name: str) -> Optional[str]:
        """Use vector search to find best matching course by name"""
        try:
            results = self.course_catalog.query(
                query_texts=[course_name],
                n_results=1
            )
            
            if results['documents'][0] and results['metadatas'][0]:
                # Return the title (which is now the ID)
                return results['metadatas'][0][0]['title']
        except Exception as e:
            print(f"Error resolving course name: {e}")
        
        return None
    
    def _build_filter(self, course_title: Optional[str], lesson_number: Optional[int]) -> Optional[Dict]:
        """Build ChromaDB filter from search parameters"""
        if not course_title and lesson_number is None:
            return None
            
        # Handle different filter combinations
        if course_title and lesson_number is not None:
            return {"$and": [
                {"course_title": course_title},
                {"lesson_number": lesson_number}
            ]}
        
        if course_title:
            return {"course_title": course_title}
            
        return {"lesson_number": lesson_number}
    
    def add_course_metadata(self, course: Course):
        """Add course information to the catalog for semantic search"""
        import json

        course_text = course.title
        
        # Build lessons metadata and serialize as JSON string
        lessons_metadata = []
        for lesson in course.lessons:
            lessons_metadata.append({
                "lesson_number": lesson.lesson_number,
                "lesson_title": lesson.title,
                "lesson_link": lesson.lesson_link
            })
        
        self.course_catalog.add(
            documents=[course_text],
            metadatas=[{
                "title": course.title,
                "instructor": course.instructor,
                "course_link": course.course_link,
                "lessons_json": json.dumps(lessons_metadata),  # Serialize as JSON string
                "lesson_count": len(course.lessons)
            }],
            ids=[course.title]
        )
    
    def add_course_content(self, chunks: List[CourseChunk]):
        """Add course content chunks to the vector store"""
        if not chunks:
            return
        
        documents = [chunk.content for chunk in chunks]
        metadatas = [{
            "course_title": chunk.course_title,
            "lesson_number": chunk.lesson_number,
            "chunk_index": chunk.chunk_index
        } for chunk in chunks]
        # Use title with chunk index for unique IDs
        ids = [f"{chunk.course_title.replace(' ', '_')}_{chunk.chunk_index}" for chunk in chunks]
        
        self.course_content.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def clear_all_data(self):
        """Clear all data from both collections"""
        try:
            self.client.delete_collection("course_catalog")
            self.client.delete_collection("course_content")
            # Recreate collections
            self.course_catalog = self._create_collection("course_catalog")
            self.course_content = self._create_collection("course_content")
        except Exception as e:
            print(f"Error clearing data: {e}")
    
    def get_existing_course_titles(self) -> List[str]:
        """Get all existing course titles from the vector store"""
        try:
            # Get all documents from the catalog
            results = self.course_catalog.get()
            if results and 'ids' in results:
                return results['ids']
            return []
        except Exception as e:
            print(f"Error getting existing course titles: {e}")
            return []
    
    def get_course_count(self) -> int:
        """Get the total number of courses in the vector store"""
        try:
            results = self.course_catalog.get()
            if results and 'ids' in results:
                return len(results['ids'])
            return 0
        except Exception as e:
            print(f"Error getting course count: {e}")
            return 0
    
    def get_all_courses_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all courses in the vector store"""
        import json
        try:
            results = self.course_catalog.get()
            if results and 'metadatas' in results:
                # Parse lessons JSON for each course
                parsed_metadata = []
                for metadata in results['metadatas']:
                    course_meta = metadata.copy()
                    if 'lessons_json' in course_meta:
                        course_meta['lessons'] = json.loads(course_meta['lessons_json'])
                        del course_meta['lessons_json']  # Remove the JSON string version
                    parsed_metadata.append(course_meta)
                return parsed_metadata
            return []
        except Exception as e:
            print(f"Error getting courses metadata: {e}")
            return []

    def get_course_link(self, course_title: str) -> Optional[str]:
        """Get course link for a given course title"""
        try:
            # Get course by ID (title is the ID)
            results = self.course_catalog.get(ids=[course_title])
            if results and 'metadatas' in results and results['metadatas']:
                metadata = results['metadatas'][0]
                return metadata.get('course_link')
            return None
        except Exception as e:
            print(f"Error getting course link: {e}")
            return None
    
    def get_lesson_link(self, course_title: str, lesson_number: int) -> Optional[str]:
        """Get lesson link for a given course title and lesson number"""
        import json
        try:
            # Get course by ID (title is the ID)
            results = self.course_catalog.get(ids=[course_title])
            if results and 'metadatas' in results and results['metadatas']:
                metadata = results['metadatas'][0]
                lessons_json = metadata.get('lessons_json')
                if lessons_json:
                    lessons = json.loads(lessons_json)
                    # Find the lesson with matching number
                    for lesson in lessons:
                        if lesson.get('lesson_number') == lesson_number:
                            return lesson.get('lesson_link')
            return None
        except Exception as e:
            print(f"Error getting lesson link: {e}")
            return None
    
    # New methods for business documents
    
    def add_document_metadata(self, document: BusinessDocument):
        """Add document information to the catalog for semantic search with enhanced metadata"""
        import json

        document_text = document.title
        
        # Build enhanced document metadata (ChromaDB doesn't accept None values)
        metadata = {
            "title": document.title,
            "file_path": document.file_path,
            "file_type": document.file_type,
            "doc_type": document.doc_type.value,
            "version": document.version.value,
            "confidentiality": document.confidentiality.value,
            "entities": json.dumps(document.entities),  # Store as JSON array
            "metadata_json": json.dumps(document.metadata)  # Legacy metadata field
        }
        
        # Only add non-None values
        if document.file_size is not None:
            metadata["file_size"] = document.file_size
        
        if document.created_date is not None:
            metadata["created_date"] = document.created_date.isoformat()
        
        if document.effective_date is not None:
            metadata["effective_date"] = document.effective_date.isoformat()
        
        if document.address is not None:
            metadata["address"] = document.address
        
        if document.notes is not None:
            metadata["notes"] = document.notes
        
        if document.content_hash is not None:
            metadata["content_hash"] = document.content_hash
        
        self.document_catalog.add(
            documents=[document_text],
            metadatas=[metadata],
            ids=[document.title]
        )
    
    def add_document_content(self, chunks: List[DocumentChunk]):
        """Add document content chunks to the vector store with enhanced metadata"""
        if not chunks:
            return
        
        import json
        documents = [chunk.content for chunk in chunks]
        metadatas = []
        
        for chunk in chunks:
            metadata = {
                "document_title": chunk.document_title,
                "file_type": chunk.file_type,
                "doc_type": chunk.doc_type.value,
                "chunk_index": chunk.chunk_index,
                "version": chunk.version.value,
                "entities": json.dumps(chunk.entities)  # Store as JSON array
            }
            
            # Only add non-None values for source attribution
            if chunk.section_title is not None:
                metadata["section_title"] = chunk.section_title
            if chunk.page_number is not None:
                metadata["page_number"] = chunk.page_number
            if chunk.sheet_name is not None:
                metadata["sheet_name"] = chunk.sheet_name
            if chunk.cell_range is not None:
                metadata["cell_range"] = chunk.cell_range
            if chunk.row_number is not None:
                metadata["row_number"] = chunk.row_number
            if chunk.effective_date is not None:
                metadata["effective_date"] = chunk.effective_date.isoformat()
            
            metadatas.append(metadata)
        
        # Use title with chunk index for unique IDs
        ids = [f"{chunk.document_title.replace(' ', '_')}_{chunk.chunk_index}" for chunk in chunks]
        
        self.document_content.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def get_existing_document_titles(self) -> List[str]:
        """Get all existing document titles from the vector store"""
        try:
            # Get all documents from the catalog
            results = self.document_catalog.get()
            if results and 'ids' in results:
                return results['ids']
            return []
        except Exception as e:
            print(f"Error getting existing document titles: {e}")
            return []
    
    def get_document_count(self) -> int:
        """Get the total number of documents in the vector store"""
        try:
            results = self.document_catalog.get()
            if results and 'ids' in results:
                return len(results['ids'])
            return 0
        except Exception as e:
            print(f"Error getting document count: {e}")
            return 0
    
    def document_exists(self, content_hash: str) -> bool:
        """Check if a document with the given content hash already exists"""
        try:
            # Query the document catalog for documents with this content hash
            results = self.document_catalog.get(
                where={"content_hash": content_hash}
            )
            return len(results.get('ids', [])) > 0
        except Exception as e:
            print(f"Error checking document existence: {e}")
            return False
    
    def search_documents_enhanced(self, query: str, document_title: Optional[str] = None, 
                                doc_type: Optional[str] = None, entity: Optional[str] = None,
                                year: Optional[int] = None, file_type: Optional[str] = None,
                                limit: Optional[int] = None) -> SearchResults:
        """
        Enhanced search interface for business documents with structured filtering.
        
        Args:
            query: What to search for in document content
            document_title: Optional document title to filter by
            doc_type: Optional business document type (formation, insurance, etc.)
            entity: Optional entity name to filter by
            year: Optional year to filter by effective date
            file_type: Optional file type (pdf, docx, xlsx, etc.)
            limit: Maximum results to return
            
        Returns:
            SearchResults object with documents and metadata
        """
        # Step 1: Resolve document title if provided
        resolved_title = None
        if document_title:
            resolved_title = self._resolve_document_title(document_title)
            if not resolved_title:
                return SearchResults.empty(f"No document found matching '{document_title}'")
        
        # Step 2: Build enhanced filter for content search
        filter_dict = self._build_enhanced_document_filter(
            resolved_title, doc_type, entity, year, file_type
        )
        
        # Step 3: Search document content
        search_limit = limit if limit is not None else self.max_results
        
        try:
            # Query the document content collection with filters
            if filter_dict:
                results = self.document_content.query(
                    query_texts=[query],
                    n_results=search_limit,
                    where=filter_dict
                )
            else:
                results = self.document_content.query(
                    query_texts=[query],
                    n_results=search_limit
                )
            
            return SearchResults.from_chroma(results)
            
        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            print(error_msg)
            return SearchResults.empty(error_msg)
    
    def _build_enhanced_document_filter(self, document_title: Optional[str], doc_type: Optional[str],
                                      entity: Optional[str], year: Optional[int],
                                      file_type: Optional[str]) -> Optional[Dict]:
        """Build enhanced filter dictionary for ChromaDB queries

        Note: Entity filtering is not supported because entities are stored as JSON strings
        and ChromaDB doesn't support text search operators like $contains. Entity filtering
        must be done post-query if needed.
        """
        filters = {}

        # Document title filter
        if document_title:
            filters["document_title"] = document_title

        # Business document type filter
        if doc_type:
            filters["doc_type"] = doc_type

        # File type filter
        if file_type:
            filters["file_type"] = file_type

        # Entity filter - NOT SUPPORTED by ChromaDB
        # ChromaDB only supports: $gt, $gte, $lt, $lte, $ne, $eq, $in, $nin
        # Since entities are stored as JSON strings, we can't query them directly
        # Entity filtering would need to be done post-query in Python if needed
        if entity:
            # Log warning but don't add to filters to avoid ChromaDB error
            print(f"Warning: Entity filter '{entity}' is not supported in ChromaDB queries. Ignoring.")

        # Year filter - search effective dates
        if year:
            # Filter for dates in the specified year
            year_start = f"{year}-01-01"
            year_end = f"{year}-12-31"
            filters["effective_date"] = {"$gte": year_start, "$lte": year_end}

        return filters if filters else None
    
    def search_documents(self, 
                        query: str,
                        document_title: Optional[str] = None,
                        document_type: Optional[str] = None,
                        limit: Optional[int] = None) -> SearchResults:
        """
        Search interface specifically for business documents.
        
        Args:
            query: What to search for in document content
            document_title: Optional document title to filter by
            document_type: Optional document type to filter by (pdf, docx, txt)
            limit: Maximum results to return
            
        Returns:
            SearchResults object with documents and metadata
        """
        # Step 1: Resolve document title if provided
        resolved_title = None
        if document_title:
            resolved_title = self._resolve_document_title(document_title)
            if not resolved_title:
                return SearchResults.empty(f"No document found matching '{document_title}'")
        
        # Step 2: Build filter for content search
        filter_dict = self._build_document_filter(resolved_title, document_type)
        
        # Step 3: Search document content
        # Use provided limit or fall back to configured max_results
        search_limit = limit if limit is not None else self.max_results
        
        try:
            results = self.document_content.query(
                query_texts=[query],
                n_results=search_limit,
                where=filter_dict
            )
            return SearchResults.from_chroma(results)
        except Exception as e:
            return SearchResults.empty(f"Search error: {str(e)}")
    
    def _resolve_document_title(self, document_title: str) -> Optional[str]:
        """Use vector search to find best matching document by title"""
        try:
            results = self.document_catalog.query(
                query_texts=[document_title],
                n_results=1
            )
            
            if results['documents'][0] and results['metadatas'][0]:
                # Return the title (which is now the ID)
                return results['metadatas'][0][0]['title']
        except Exception as e:
            print(f"Error resolving document title: {e}")
        
        return None
    
    def _build_document_filter(self, document_title: Optional[str], document_type: Optional[str]) -> Optional[Dict]:
        """Build ChromaDB filter from document search parameters"""
        if not document_title and not document_type:
            return None
            
        # Handle different filter combinations
        if document_title and document_type:
            return {"$and": [
                {"document_title": document_title},
                {"document_type": document_type}
            ]}
        
        if document_title:
            return {"document_title": document_title}
            
        return {"document_type": document_type}
    
    def get_all_documents_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all documents in the vector store"""
        import json
        try:
            results = self.document_catalog.get()
            if results and 'metadatas' in results:
                # Parse metadata JSON for each document
                parsed_metadata = []
                for metadata in results['metadatas']:
                    doc_meta = metadata.copy()
                    if 'metadata_json' in doc_meta:
                        doc_meta['metadata'] = json.loads(doc_meta['metadata_json'])
                        del doc_meta['metadata_json']  # Remove the JSON string version
                    parsed_metadata.append(doc_meta)
                return parsed_metadata
            return []
        except Exception as e:
            print(f"Error getting documents metadata: {e}")
            return []
    
    def get_document_by_title(self, document_title: str) -> Optional[Dict[str, Any]]:
        """Get document metadata for a given document title"""
        import json
        try:
            # Get document by ID (title is the ID)
            results = self.document_catalog.get(ids=[document_title])
            if results and 'metadatas' in results and results['metadatas']:
                metadata = results['metadatas'][0]
                # Parse metadata JSON if it exists
                if 'metadata_json' in metadata:
                    metadata['metadata'] = json.loads(metadata['metadata_json'])
                    del metadata['metadata_json']
                return metadata
            return None
        except Exception as e:
            print(f"Error getting document metadata: {e}")
            return None
    
    def clear_document_data(self):
        """Clear all document data from both collections"""
        try:
            self.client.delete_collection("document_catalog")
            self.client.delete_collection("document_content")
            # Recreate collections
            self.document_catalog = self._create_collection("document_catalog")
            self.document_content = self._create_collection("document_content")
        except Exception as e:
            print(f"Error clearing document data: {e}")
    
    def get_documents_by_type(self, document_type: str) -> List[str]:
        """Get all document titles of a specific type"""
        try:
            results = self.document_catalog.get()
            if results and 'metadatas' in results and 'ids' in results:
                filtered_titles = []
                for i, metadata in enumerate(results['metadatas']):
                    if metadata.get('document_type') == document_type:
                        filtered_titles.append(results['ids'][i])
                return filtered_titles
            return []
        except Exception as e:
            print(f"Error getting documents by type: {e}")
            return []