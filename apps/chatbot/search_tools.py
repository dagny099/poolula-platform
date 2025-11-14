from typing import Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
from .vector_store import VectorStore, SearchResults
from .database_tool import DatabaseQueryTool, execute_database_query, get_database_tool_definition


class Tool(ABC):
    """Abstract base class for all tools"""
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass


class CourseSearchTool(Tool):
    """Tool for searching course content with semantic course name matching"""
    
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last search
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "What to search for in the course content"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"
                    },
                    "lesson_number": {
                        "type": "integer",
                        "description": "Specific lesson number to search within (e.g. 1, 2, 3)"
                    }
                },
                "required": ["query"]
            }
        }
    
    def execute(self, query: str, course_name: Optional[str] = None, lesson_number: Optional[int] = None) -> str:
        """
        Execute the search tool with given parameters.
        
        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter
            
        Returns:
            Formatted search results or error message
        """
        
        # Use the vector store's unified search interface
        results = self.store.search(
            query=query,
            course_name=course_name,
            lesson_number=lesson_number
        )
        
        # Handle errors
        if results.error:
            return results.error
        
        # Handle empty results
        if results.is_empty():
            filter_info = ""
            if course_name:
                filter_info += f" in course '{course_name}'"
            if lesson_number:
                filter_info += f" in lesson {lesson_number}"
            return f"No relevant content found{filter_info}."
        
        # Format and return results
        return self._format_results(results)
    
    def _format_results(self, results: SearchResults) -> str:
        """Format search results with course and lesson context"""
        formatted = []
        sources = []  # Track sources for the UI with links
        
        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get('course_title', 'unknown')
            lesson_num = meta.get('lesson_number')
            
            # Build context header
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"
            
            # Build source with link information
            source_text = course_title
            if lesson_num is not None:
                source_text += f" - Lesson {lesson_num}"
            
            # Try to get lesson link
            lesson_link = None
            if lesson_num is not None:
                lesson_link = self.store.get_lesson_link(course_title, lesson_num)
            
            # Create source object with text and optional link
            source_obj = {
                "text": source_text,
                "link": lesson_link,
                "course_title": course_title,
                "lesson_number": lesson_num
            }
            sources.append(source_obj)
            
            formatted.append(f"{header}\n{doc}")
        
        # Store sources for retrieval
        self.last_sources = sources
        
        return "\n\n".join(formatted)


class CourseOutlineTool(Tool):
    """Tool for retrieving course outlines with title, link, and lesson list"""
    
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last search
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "get_course_outline",
            "description": "Get course outline including title, link, and complete lesson list",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_title": {
                        "type": "string",
                        "description": "Course title or partial name (fuzzy matching supported)"
                    }
                },
                "required": ["course_title"]
            }
        }
    
    def execute(self, course_title: str) -> str:
        """
        Execute the outline tool to get course structure.
        
        Args:
            course_title: Course name to get outline for
            
        Returns:
            Formatted course outline or error message
        """
        # First, resolve the course name using vector search
        resolved_title = self.store._resolve_course_name(course_title)
        
        if not resolved_title:
            return f"No course found matching '{course_title}'"
        
        # Get all courses metadata to find the specific course
        all_courses = self.store.get_all_courses_metadata()
        
        target_course = None
        for course in all_courses:
            if course.get('title') == resolved_title:
                target_course = course
                break
        
        if not target_course:
            return f"Course metadata not found for '{resolved_title}'"
        
        # Format the outline response
        return self._format_course_outline(target_course)
    
    def _format_course_outline(self, course_data: Dict[str, Any]) -> str:
        """Format course data into a readable outline"""
        title = course_data.get('title', 'Unknown Course')
        course_link = course_data.get('course_link', 'Not available')
        lessons = course_data.get('lessons', [])
        
        # Build the formatted outline
        outline_parts = [
            f"Course: {title}",
            f"Link: {course_link}" if course_link and course_link != 'Not available' else "Link: Not available"
        ]
        
        if lessons:
            outline_parts.append("Lessons:")
            # Sort lessons by lesson number to ensure proper order
            sorted_lessons = sorted(lessons, key=lambda x: x.get('lesson_number', 0))
            for lesson in sorted_lessons:
                lesson_num = lesson.get('lesson_number', '?')
                lesson_title = lesson.get('lesson_title', 'Untitled Lesson')
                outline_parts.append(f"{lesson_num}. {lesson_title}")
        else:
            outline_parts.append("No lessons available")
        
        # Store source information for UI
        source_obj = {
            "text": f"{title} - Course Outline",
            "link": course_link if course_link and course_link != 'Not available' else None,
            "course_title": title,
            "lesson_number": None
        }
        self.last_sources = [source_obj]
        
        return "\n".join(outline_parts)


class ToolManager:
    """Manages available tools for the AI"""
    
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, tool: Tool):
        """Register any tool that implements the Tool interface"""
        tool_def = tool.get_tool_definition()
        tool_name = tool_def.get("name")
        if not tool_name:
            raise ValueError("Tool must have a 'name' in its definition")
        self.tools[tool_name] = tool

    
    def get_tool_definitions(self) -> list:
        """Get all tool definitions for Anthropic tool calling"""
        return [tool.get_tool_definition() for tool in self.tools.values()]
    
    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"
        
        return self.tools[tool_name].execute(**kwargs)
    
    def get_last_sources(self) -> list:
        """Get sources from the last search operation"""
        # Check all tools for last_sources attribute
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources') and tool.last_sources:
                return tool.last_sources
        return []

    def reset_sources(self):
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources'):
                tool.last_sources = []


class DocumentSearchTool(Tool):
    """Tool for searching business document content with semantic document name matching"""
    
    def __init__(self, vector_store: VectorStore, cache_manager=None):
        self.store = vector_store
        self.cache_manager = cache_manager  # Optional cache manager
        self.last_sources = []  # Track sources from last search
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool with enhanced filtering"""
        return {
            "name": "search_document_content",
            "description": "Search business documents with advanced filtering by document type, entities, dates, and content. Supports formation docs, insurance policies, tax documents, meeting minutes, contracts, and more.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "What to search for in the business documents (e.g., 'business purpose', 'tax deadline', 'LLC assets', 'insurance coverage')"
                    },
                    "document_title": {
                        "type": "string",
                        "description": "Document filename or partial title to search within (e.g., 'Articles', 'Minutes', 'Insurance')"
                    },
                    "doc_type": {
                        "type": "string",
                        "description": "Business document classification: formation, authority, deed, insurance, banking, accounting, minutes, consent, compliance, lease, vendor, tax, index",
                        "enum": ["formation", "authority", "deed", "insurance", "banking", "accounting", "minutes", "consent", "compliance", "lease", "vendor", "tax", "index"]
                    },
                    "entity": {
                        "type": "string",
                        "description": "Filter by entity name (e.g., 'Poolula LLC', 'Hidalgo-Sotelo Living Trust', 'Rosalba Sotelo')"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Filter by year (e.g., 2024, 2023) - searches effective dates"
                    },
                    "file_type": {
                        "type": "string",
                        "description": "File format: pdf, docx, txt, xlsx, csv",
                        "enum": ["pdf", "docx", "txt", "xlsx", "csv"]
                    }
                },
                "required": ["query"]
            }
        }
    
    def execute(self, query: str, document_title: Optional[str] = None, doc_type: Optional[str] = None, 
                entity: Optional[str] = None, year: Optional[int] = None, file_type: Optional[str] = None, 
                document_type: Optional[str] = None) -> str:
        """Execute document search with enhanced filtering capabilities and caching"""
        try:
            # Handle legacy document_type parameter (map to file_type)
            if document_type and not file_type:
                file_type = document_type
            
            # Check cache if available
            cache_key_filters = {
                'document_title': document_title,
                'doc_type': doc_type,
                'entity': entity,
                'year': year,
                'file_type': file_type
            }
            
            cached_result = None
            if self.cache_manager:
                cached_result = self.cache_manager.get(query, cache_key_filters)
            
            if cached_result:
                # Restore sources from cached result
                if 'sources' in cached_result:
                    self.last_sources = cached_result['sources']
                return cached_result['response']
            
            # Use the enhanced document search method from vector store
            results = self.store.search_documents_enhanced(
                query=query,
                document_title=document_title,
                doc_type=doc_type,
                entity=entity,
                year=year,
                file_type=file_type
            )
            
            if results.is_empty():
                filters_desc = self._build_filter_description(document_title, doc_type, entity, year, file_type)
                response = f"No results found for '{query}'{filters_desc}"
            else:
                response = self._format_document_results_enhanced(results)
            
            # Cache the result if cache manager is available
            if self.cache_manager:
                cache_data = {
                    'response': response,
                    'sources': self.last_sources.copy()  # Store sources in cache
                }
                self.cache_manager.set(query, cache_data, cache_key_filters)
            
            return response
            
        except Exception as e:
            return f"Error searching documents: {str(e)}"
    
    def _build_filter_description(self, document_title: Optional[str], doc_type: Optional[str], 
                                 entity: Optional[str], year: Optional[int], file_type: Optional[str]) -> str:
        """Build a human-readable description of applied filters"""
        filters = []
        if document_title:
            filters.append(f"in document '{document_title}'")
        if doc_type:
            filters.append(f"in {doc_type} documents")
        if entity:
            filters.append(f"related to {entity}")
        if year:
            filters.append(f"from {year}")
        if file_type:
            filters.append(f"in {file_type.upper()} files")
        
        if filters:
            return " " + " and ".join(filters)
        return ""
    
    def _format_document_results(self, results: SearchResults) -> str:
        """Format search results for display (legacy method)"""
        return self._format_document_results_enhanced(results)
    
    def _format_document_results_enhanced(self, results: SearchResults) -> str:
        """Format search results for display with enhanced metadata"""
        formatted = []
        sources = []
        
        for i, (doc, metadata) in enumerate(zip(results.documents, results.metadata)):
            doc_title = metadata.get('document_title', 'Unknown Document')
            file_type = metadata.get('file_type', metadata.get('document_type', 'unknown'))
            doc_type = metadata.get('doc_type', 'unknown')
            
            # Enhanced source attribution
            page_num = metadata.get('page_number')
            section = metadata.get('section_title')
            sheet_name = metadata.get('sheet_name')
            cell_range = metadata.get('cell_range')
            row_number = metadata.get('row_number')
            
            # Build header with enhanced source info
            header = f"[Document: {doc_title}"
            
            # Add location information based on file type
            if page_num:
                header += f" - Page {page_num}"
            elif sheet_name:
                header += f" - Sheet: {sheet_name}"
                if cell_range:
                    header += f", Range: {cell_range}"
            elif row_number:
                header += f" - Row {row_number}"
            
            if section:
                header += f" - {section}"
            
            header += f" ({file_type.upper()}, {doc_type.upper()})]"
            
            # Build source information for UI
            source_text = doc_title
            if page_num:
                source_text += f" - Page {page_num}"
            elif sheet_name:
                source_text += f" - Sheet: {sheet_name}"
                if cell_range:
                    source_text += f" ({cell_range})"
            elif row_number:
                source_text += f" - Row {row_number}"
            
            # Create enhanced source object
            source_obj = {
                "text": source_text,
                "document_title": doc_title,
                "file_type": file_type,
                "doc_type": doc_type,
                "page_number": page_num,
                "section_title": section,
                "sheet_name": sheet_name,
                "cell_range": cell_range,
                "row_number": row_number
            }
            sources.append(source_obj)
            
            formatted.append(f"{header}\n{doc}")
        
        # Store sources for retrieval
        self.last_sources = sources
        
        return "\n\n".join(formatted)


class DocumentListTool(Tool):
    """Tool for listing available business documents and their metadata"""
    
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "list_business_documents",
            "description": "List all available business documents including their types and basic information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "document_type": {
                        "type": "string",
                        "description": "Optional filter by document type: 'pdf', 'docx', or 'txt'"
                    }
                },
                "required": []
            }
        }
    
    def execute(self, document_type: Optional[str] = None) -> str:
        """Execute document listing"""
        try:
            if document_type:
                # Get documents of specific type
                document_titles = self.store.get_documents_by_type(document_type)
                if not document_titles:
                    return f"No {document_type} documents found"
                
                result = f"Available {document_type.upper()} documents:\n"
                for title in document_titles:
                    result += f"- {title}\n"
                return result.strip()
            else:
                # Get all documents
                all_docs_metadata = self.store.get_all_documents_metadata()
                if not all_docs_metadata:
                    return "No business documents found"
                
                result = "Available business documents:\n"
                for doc_meta in all_docs_metadata:
                    title = doc_meta.get('title', 'Unknown')
                    doc_type = doc_meta.get('document_type', 'unknown')
                    file_size = doc_meta.get('file_size')
                    
                    size_str = ""
                    if file_size:
                        if file_size > 1024 * 1024:
                            size_str = f" ({file_size / (1024 * 1024):.1f} MB)"
                        elif file_size > 1024:
                            size_str = f" ({file_size / 1024:.1f} KB)"
                        else:
                            size_str = f" ({file_size} bytes)"
                    
                    result += f"- {title} ({doc_type.upper()}){size_str}\n"
                
                return result.strip()
                
        except Exception as e:
            return f"Error listing documents: {str(e)}"


class DatabaseTool(Tool):
    """Tool for querying business database (properties, transactions, documents, obligations)"""

    def __init__(self):
        self.db_tool = DatabaseQueryTool()
        self.last_sources = []

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return get_database_tool_definition()

    def execute(self, query_type: str, filters: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute database query with given parameters.

        Args:
            query_type: Type of query (properties, transactions, etc.)
            filters: Optional filters for the query

        Returns:
            JSON string with query results
        """
        result = execute_database_query(query_type, filters)

        # Track sources for database queries
        # Database queries don't have traditional "sources" like documents,
        # but we can track what type of data was queried
        self.last_sources = [{
            "text": f"Database Query: {query_type}",
            "query_type": query_type,
            "filters": filters or {}
        }]

        return result