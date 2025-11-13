"""
Health check utilities for system monitoring and diagnostics
"""

import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class HealthChecker:
    """System health monitoring and diagnostics"""
    
    def __init__(self, config):
        self.config = config
        self.start_time = time.time()
    
    def get_system_health(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "uptime_seconds": int(time.time() - self.start_time),
                "components": {}
            }
            
            # Check database connectivity
            health_status["components"]["database"] = self._check_database()
            
            # Check document storage
            health_status["components"]["document_store"] = self._check_document_storage()
            
            # Check AI service connectivity
            health_status["components"]["ai_service"] = self._check_ai_service()
            
            # Check configuration
            health_status["components"]["configuration"] = self._check_configuration()
            
            # Determine overall health
            component_statuses = [comp["status"] for comp in health_status["components"].values()]
            if any(status == "error" for status in component_statuses):
                health_status["status"] = "error"
            elif any(status == "warning" for status in component_statuses):
                health_status["status"] = "warning"
                
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _check_database(self) -> Dict[str, Any]:
        """Check ChromaDB connectivity and status"""
        try:
            db_path = Path(self.config.CHROMA_PATH)
            if not db_path.exists():
                return {
                    "status": "warning",
                    "message": "Database directory does not exist",
                    "path": str(db_path)
                }
            
            # Check if database is accessible
            db_size = sum(f.stat().st_size for f in db_path.rglob('*') if f.is_file())
            
            return {
                "status": "healthy",
                "message": "Database accessible",
                "path": str(db_path),
                "size_bytes": db_size
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Database check failed: {str(e)}"
            }
    
    def _check_document_storage(self) -> Dict[str, Any]:
        """Check document storage accessibility"""
        try:
            docs_path = Path(self.config.DOCS_PATH)
            
            if not docs_path.exists():
                return {
                    "status": "warning",
                    "message": "Documents directory does not exist",
                    "path": str(docs_path)
                }
            
            # Count documents
            processed_path = docs_path / "processed"
            incoming_path = docs_path / "incoming"
            
            processed_count = len(list(processed_path.glob("*"))) if processed_path.exists() else 0
            incoming_count = len(list(incoming_path.glob("*"))) if incoming_path.exists() else 0
            
            return {
                "status": "healthy",
                "message": "Document storage accessible",
                "processed_documents": processed_count,
                "incoming_documents": incoming_count,
                "path": str(docs_path)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Document storage check failed: {str(e)}"
            }
    
    def _check_ai_service(self) -> Dict[str, Any]:
        """Check AI service configuration"""
        try:
            if not self.config.ANTHROPIC_API_KEY:
                return {
                    "status": "error",
                    "message": "Anthropic API key not configured"
                }
            
            if len(self.config.ANTHROPIC_API_KEY) < 20:
                return {
                    "status": "warning",
                    "message": "API key appears to be invalid"
                }
            
            return {
                "status": "healthy",
                "message": "AI service configured",
                "model": self.config.ANTHROPIC_MODEL
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"AI service check failed: {str(e)}"
            }
    
    def _check_configuration(self) -> Dict[str, Any]:
        """Check system configuration"""
        try:
            config_issues = []
            
            # Check chunk size
            if self.config.CHUNK_SIZE < 500:
                config_issues.append("Chunk size may be too small")
            elif self.config.CHUNK_SIZE > 5000:
                config_issues.append("Chunk size may be too large")
            
            # Check cache settings
            if self.config.CACHE_TTL_MINUTES < 1:
                config_issues.append("Cache TTL may be too short")
            
            status = "warning" if config_issues else "healthy"
            message = "; ".join(config_issues) if config_issues else "Configuration valid"
            
            return {
                "status": status,
                "message": message,
                "chunk_size": self.config.CHUNK_SIZE,
                "cache_ttl_minutes": self.config.CACHE_TTL_MINUTES
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Configuration check failed: {str(e)}"
            }

def create_health_endpoint(health_checker: HealthChecker):
    """Factory function to create health check endpoint"""
    def health_check() -> Dict[str, Any]:
        return health_checker.get_system_health()
    
    return health_check