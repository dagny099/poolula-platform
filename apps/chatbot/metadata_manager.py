import os
import csv
from typing import Dict, List, Optional, Any
from datetime import datetime
from .models import DocumentMetadata, DocumentType, VersionStatus, ConfidentialityLevel

class MetadataManager:
    """Manages document metadata from CSV files and provides business logic for document classification"""
    
    def __init__(self, metadata_csv_path: str):
        self.metadata_csv_path = metadata_csv_path
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from CSV file into memory cache"""
        self._metadata_cache.clear()
        
        if not os.path.exists(self.metadata_csv_path):
            print(f"Metadata CSV not found at {self.metadata_csv_path}, using default metadata")
            return
        
        try:
            with open(self.metadata_csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    if row.get('doc_id'):
                        # Parse entities from comma-separated string to list
                        entities = []
                        if row.get('entities'):
                            entities = [entity.strip() for entity in row['entities'].split(',') if entity.strip()]
                        
                        # Parse effective_date if provided
                        effective_date = None
                        if row.get('effective_date'):
                            try:
                                effective_date = datetime.fromisoformat(row['effective_date'])
                            except ValueError:
                                print(f"Invalid date format for {row['doc_id']}: {row['effective_date']}")
                        
                        # Store processed metadata
                        self._metadata_cache[row['doc_id']] = {
                            'title': row.get('title', row['doc_id']),
                            'doc_type': row.get('doc_type', 'index'),
                            'effective_date': effective_date,
                            'entities': entities,
                            'address': row.get('address'),
                            'version': row.get('version', 'final'),
                            'confidentiality': row.get('confidentiality', 'internal'),
                            'notes': row.get('notes')
                        }
        except Exception as e:
            print(f"Error loading metadata CSV: {e}")
    
    def get_metadata_for_file(self, file_path: str) -> Dict[str, Any]:
        """Get metadata for a specific file, with intelligent defaults if not found in CSV"""
        filename = os.path.basename(file_path)
        
        # First, check if we have explicit metadata
        if filename in self._metadata_cache:
            return self._metadata_cache[filename]
        
        # If no explicit metadata, try to infer from filename
        return self._infer_metadata_from_filename(filename, file_path)
    
    def _infer_metadata_from_filename(self, filename: str, file_path: str) -> Dict[str, Any]:
        """Intelligently infer document metadata from filename patterns"""
        filename_lower = filename.lower()
        
        # Default metadata
        metadata = {
            'title': filename,
            'doc_type': 'index',  # Default fallback
            'effective_date': None,
            'entities': ["Poolula LLC"],  # Default entity
            'address': None,
            'version': 'final',
            'confidentiality': 'internal',
            'notes': 'Auto-inferred from filename'
        }
        
        # Infer document type from filename patterns
        if any(term in filename_lower for term in ['article', 'formation', 'organizing']):
            metadata['doc_type'] = 'formation'
        elif any(term in filename_lower for term in ['authority', 'statement', 'trust']):
            metadata['doc_type'] = 'authority'
        elif any(term in filename_lower for term in ['deed', 'closing', 'title']):
            metadata['doc_type'] = 'deed'
        elif any(term in filename_lower for term in ['insurance', 'policy', 'declaration', 'travelers']):
            metadata['doc_type'] = 'insurance'
        elif any(term in filename_lower for term in ['bank', 'account', 'credit']):
            metadata['doc_type'] = 'banking'
        elif any(term in filename_lower for term in ['accounting', 'chart', 'ledger', 'financial']):
            metadata['doc_type'] = 'accounting'
        elif any(term in filename_lower for term in ['minutes', 'meeting']):
            metadata['doc_type'] = 'minutes'
        elif any(term in filename_lower for term in ['consent', 'resolution']):
            metadata['doc_type'] = 'consent'
        elif any(term in filename_lower for term in ['compliance', 'report', 'periodic']):
            metadata['doc_type'] = 'compliance'
        elif any(term in filename_lower for term in ['lease', 'rental', 'tenant']):
            metadata['doc_type'] = 'lease'
        elif any(term in filename_lower for term in ['vendor', 'contract', 'service']):
            metadata['doc_type'] = 'vendor'
        elif any(term in filename_lower for term in ['tax', '1065', 'extension']):
            metadata['doc_type'] = 'tax'
        
        # Try to extract year from filename for effective_date
        import re
        year_match = re.search(r'20[12]\d', filename)
        if year_match:
            try:
                year = int(year_match.group())
                metadata['effective_date'] = datetime(year, 1, 1)
            except:
                pass
        
        # Infer entities from filename patterns
        entities = ["Poolula LLC"]
        if any(term in filename_lower for term in ['trust', 'hidalgo', 'sotelo']):
            entities.append("Hidalgo-Sotelo Living Trust")
            entities.append("Rosalba Sotelo")
        
        metadata['entities'] = entities
        
        return metadata
    
    def reload_metadata(self):
        """Reload metadata from CSV file (useful after updates)"""
        self._load_metadata()
    
    def create_sample_metadata_csv(self):
        """Create a sample metadata CSV file with Poolula-specific examples"""
        sample_data = [
            {
                'doc_id': 'Articles_of_Organization_2024.pdf',
                'title': 'Poolula LLC Articles of Organization',
                'doc_type': 'formation',
                'effective_date': '2024-01-15',
                'entities': 'Poolula LLC, Hidalgo-Sotelo Living Trust',
                'address': '900 S 9th St, Montrose, CO',
                'version': 'final',
                'confidentiality': 'internal',
                'notes': 'Filed with Colorado Secretary of State'
            },
            {
                'doc_id': 'Statement_of_Authority_Trust.pdf',
                'title': 'Statement of Authority - Living Trust',
                'doc_type': 'authority',
                'effective_date': '2024-01-10',
                'entities': 'Hidalgo-Sotelo Living Trust, Rosalba Sotelo',
                'address': '',
                'version': 'final',
                'confidentiality': 'internal',
                'notes': 'Trustee authority documentation'
            },
            {
                'doc_id': 'Travelers_Declaration_2024.pdf',
                'title': 'Travelers Insurance Declaration Page',
                'doc_type': 'insurance',
                'effective_date': '2024-05-01',
                'entities': 'Poolula LLC',
                'address': '900 S 9th St, Montrose, CO',
                'version': 'final',
                'confidentiality': 'internal',
                'notes': 'Current property insurance policy'
            },
            {
                'doc_id': 'Annual_Meeting_Minutes_2024.pdf',
                'title': 'Annual Meeting Minutes 2024',
                'doc_type': 'minutes',
                'effective_date': '2024-12-31',
                'entities': 'Poolula LLC, Rosalba Sotelo',
                'address': '',
                'version': 'final',
                'confidentiality': 'internal',
                'notes': 'Annual LLC meeting minutes'
            }
        ]
        
        os.makedirs(os.path.dirname(self.metadata_csv_path) if os.path.dirname(self.metadata_csv_path) else '.', exist_ok=True)
        
        with open(self.metadata_csv_path, 'w', newline='', encoding='utf-8') as file:
            fieldnames = ['doc_id', 'title', 'doc_type', 'effective_date', 'entities', 'address', 'version', 'confidentiality', 'notes']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in sample_data:
                writer.writerow(row)
        
        print(f"Sample metadata CSV created at {self.metadata_csv_path}")
    
    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get all loaded metadata"""
        return self._metadata_cache.copy()
    
    def get_documents_by_type(self, doc_type: DocumentType) -> List[str]:
        """Get list of document IDs for a specific document type"""
        return [doc_id for doc_id, metadata in self._metadata_cache.items() 
                if metadata.get('doc_type') == doc_type.value]
    
    def get_documents_by_entity(self, entity: str) -> List[str]:
        """Get list of document IDs that reference a specific entity"""
        return [doc_id for doc_id, metadata in self._metadata_cache.items() 
                if entity in metadata.get('entities', [])]