#!/usr/bin/env python3
"""
Document Ingestion Script for Poolula Platform

Ingests business documents into ChromaDB vector store for semantic search.

Usage:
    # Ingest all documents from documents/ directory
    uv run python scripts/ingest_documents.py

    # Ingest specific directory
    uv run python scripts/ingest_documents.py --directory documents/formation

    # Ingest single file
    uv run python scripts/ingest_documents.py --file documents/formation/articles.pdf

    # Force re-ingestion (clear and rebuild)
    uv run python scripts/ingest_documents.py --force

    # List ingested documents
    uv run python scripts/ingest_documents.py --list

Author: Poolula Platform
Date: 2024-11-14
"""

import sys
from pathlib import Path
from typing import List, Optional
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.chatbot.document_processor import DocumentProcessor
from apps.chatbot.vector_store import VectorStore
from apps.chatbot.metadata_manager import MetadataManager
from core.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

# Configuration
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
CHROMA_PATH = "chroma_db"
EMBEDDING_MODEL = "default"  # ChromaDB uses ONNXMiniLM_L6_V2 by default
MAX_RESULTS = 5
METADATA_CSV_PATH = "data/document_metadata.csv"


class DocumentIngestor:
    """
    Handles document ingestion workflow for Poolula Platform

    Processes business documents from documents/ directory and adds them
    to ChromaDB vector store for semantic search.
    """

    def __init__(self, force_rebuild: bool = False):
        """
        Initialize document ingestor

        Args:
            force_rebuild: If True, clear existing data before ingesting
        """
        self.doc_processor = DocumentProcessor(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        self.vector_store = VectorStore(
            chroma_path=CHROMA_PATH,
            embedding_model=EMBEDDING_MODEL,
            max_results=MAX_RESULTS
        )
        self.metadata_manager = MetadataManager(METADATA_CSV_PATH)

        # Project paths
        self.project_root = Path(__file__).parent.parent
        self.documents_dir = self.project_root / "documents"

        # Clear data if force rebuild
        if force_rebuild:
            logger.info("Force rebuild requested - clearing existing document data")
            self.vector_store.clear_document_data()

    def ingest_file(self, file_path: Path) -> dict:
        """
        Ingest a single document file

        Args:
            file_path: Path to document file

        Returns:
            Dict with 'success': bool, 'skipped': bool, 'chunks': int
        """
        try:
            logger.info(f"Processing: {file_path}")

            # Get metadata for the file
            metadata = self.metadata_manager.get_metadata_for_file(str(file_path))

            # OPTIMIZATION: Extract content and compute hash BEFORE expensive chunking
            # Read file content based on type
            file_extension = file_path.suffix.lower()

            if file_extension == '.pdf':
                content = self.doc_processor.read_pdf(str(file_path))
            elif file_extension == '.docx':
                content = self.doc_processor.read_docx(str(file_path))
            elif file_extension in ['.txt', '.md']:
                content = self.doc_processor.read_text_file(str(file_path))
            else:
                # For unsupported types, fall back to full processing
                document, chunks = self.doc_processor.process_business_document(
                    str(file_path),
                    metadata
                )
                logger.info(f"  - Extracted {len(chunks)} chunks")

                if self.vector_store.document_exists(document.content_hash):
                    logger.info(f"  ⏭️  Document already exists (duplicate detected), skipping: {file_path.name}")
                    return {'success': True, 'skipped': True, 'chunks': 0}

                self.vector_store.add_document_metadata(document)
                self.vector_store.add_document_content(chunks)
                logger.info(f"  ✅ Successfully ingested: {file_path.name}")
                return {'success': True, 'skipped': False, 'chunks': len(chunks)}

            # Calculate content hash early
            import hashlib
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

            # Check for duplicate BEFORE chunking (optimization!)
            if self.vector_store.document_exists(content_hash):
                logger.info(f"  ⏭️  Document already exists (duplicate detected), skipping: {file_path.name}")
                return {'success': True, 'skipped': True, 'chunks': 0}

            # Document is new, proceed with full processing
            document, chunks = self.doc_processor.process_business_document(
                str(file_path),
                metadata
            )

            logger.info(f"  - Extracted {len(chunks)} chunks")

            # Add to vector store
            self.vector_store.add_document_metadata(document)
            self.vector_store.add_document_content(chunks)

            logger.info(f"  ✅ Successfully ingested: {file_path.name}")
            return {'success': True, 'skipped': False, 'chunks': len(chunks)}

        except Exception as e:
            logger.error(f"  ❌ Error processing {file_path}: {e}", exc_info=True)
            return {'success': False, 'skipped': False, 'chunks': 0}

    def ingest_directory(self, directory_path: Path, recursive: bool = True) -> dict:
        """
        Ingest all supported files from a directory

        Args:
            directory_path: Path to directory
            recursive: Whether to process subdirectories

        Returns:
            Summary dict with counts: total, success, failed, skipped, chunks_added
        """
        if not directory_path.exists():
            logger.error(f"❌ Directory not found: {directory_path}")
            return {"total": 0, "success": 0, "failed": 0, "skipped": 0, "chunks_added": 0}

        # Supported file extensions
        supported_extensions = {'.pdf', '.docx', '.txt', '.md', '.doc'}

        # Find files to process
        pattern = "**/*" if recursive else "*"
        files_to_process = []

        for file_path in directory_path.glob(pattern):
            # Skip README files and hidden files
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                if file_path.name != "README.md" and not file_path.name.startswith('.'):
                    files_to_process.append(file_path)

        if not files_to_process:
            logger.info(f"No supported files found in: {directory_path}")
            return {"total": 0, "success": 0, "failed": 0, "skipped": 0, "chunks_added": 0}

        logger.info(f"Found {len(files_to_process)} files to process")

        # Process each file
        success_count = 0
        skip_count = 0
        total_chunks = 0
        for file_path in files_to_process:
            result = self.ingest_file(file_path)
            if result['success']:
                success_count += 1
                if result['skipped']:
                    skip_count += 1
                total_chunks += result['chunks']

        summary = {
            "total": len(files_to_process),
            "success": success_count,
            "failed": len(files_to_process) - success_count,
            "skipped": skip_count,
            "chunks_added": total_chunks
        }

        return summary

    def ingest_all_documents(self) -> dict:
        """
        Ingest all documents from documents/ directory

        Returns:
            Summary dict with counts
        """
        logger.info(f"Ingesting documents from: {self.documents_dir}")

        if not self.documents_dir.exists():
            logger.error(f"❌ Documents directory not found: {self.documents_dir}")
            return {"total": 0, "success": 0, "failed": 0}

        return self.ingest_directory(self.documents_dir, recursive=True)

    def list_ingested_documents(self) -> None:
        """List all documents currently in the vector store"""
        try:
            logger.info("📋 Currently ingested documents:")

            # Get all document metadata from vector store
            documents = self.vector_store.get_all_documents_metadata()

            if not documents:
                logger.info("  No documents found in vector store")
                return

            # Group by doc_type
            by_type = {}
            for doc in documents:
                doc_type = doc.get('doc_type', 'unknown')
                if doc_type not in by_type:
                    by_type[doc_type] = []
                by_type[doc_type].append(doc)

            # Print grouped results
            for doc_type, docs in sorted(by_type.items()):
                logger.info(f"\n📁 {doc_type.upper()} ({len(docs)} documents):")
                for doc in sorted(docs, key=lambda x: x.get('title', '')):
                    title = doc.get('title', 'Unknown')
                    effective_date = doc.get('effective_date', 'N/A')
                    logger.info(f"  - {title} (Effective: {effective_date})")

            logger.info(f"\n Total documents: {len(documents)}")

        except Exception as e:
            logger.error(f"❌ Error listing documents: {e}", exc_info=True)

    def show_document_stats(self) -> None:
        """Show detailed statistics for all ingested documents"""
        try:
            logger.info("📊 Document Ingestion Statistics\n")

            # Get all document metadata
            documents = self.vector_store.get_all_documents_metadata()

            if not documents:
                logger.info("  No documents found in vector store")
                return

            # Get chunk counts for each document
            total_chunks = 0
            doc_stats = []

            for doc in documents:
                title = doc.get('title', 'Unknown')
                # Query chunks for this document
                chunk_results = self.vector_store.document_content.get(
                    where={"document_title": title}
                )
                chunk_count = len(chunk_results.get('ids', []))
                total_chunks += chunk_count

                doc_stats.append({
                    'title': title,
                    'doc_type': doc.get('doc_type', 'unknown'),
                    'effective_date': doc.get('effective_date', 'N/A'),
                    'entities': doc.get('entities', []),
                    'chunk_count': chunk_count,
                    'content_hash': doc.get('content_hash', 'N/A')[:12] + '...',  # First 12 chars
                    'file_type': doc.get('file_type', 'unknown'),
                    'version': doc.get('version', 'unknown')
                })

            # Sort by doc_type, then title
            doc_stats.sort(key=lambda x: (x['doc_type'], x['title']))

            # Print detailed stats
            logger.info("=" * 100)
            logger.info(f"{'TITLE':<40} {'TYPE':<12} {'CHUNKS':<8} {'DATE':<12} {'VERSION':<10}")
            logger.info("=" * 100)

            current_type = None
            for stat in doc_stats:
                # Add separator between types
                if current_type != stat['doc_type']:
                    if current_type is not None:
                        logger.info("-" * 100)
                    current_type = stat['doc_type']

                title_short = stat['title'][:38] + '..' if len(stat['title']) > 40 else stat['title']
                logger.info(
                    f"{title_short:<40} "
                    f"{stat['doc_type']:<12} "
                    f"{stat['chunk_count']:<8} "
                    f"{str(stat['effective_date'])[:12]:<12} "
                    f"{stat['version']:<10}"
                )

            logger.info("=" * 100)
            logger.info(f"\n📈 Summary:")
            logger.info(f"  - Total documents: {len(documents)}")
            logger.info(f"  - Total chunks: {total_chunks}")
            logger.info(f"  - Average chunks per document: {total_chunks / len(documents):.1f}")

            # Count by type
            type_counts = {}
            for doc in documents:
                doc_type = doc.get('doc_type', 'unknown')
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

            logger.info(f"\n📂 Documents by type:")
            for doc_type, count in sorted(type_counts.items()):
                logger.info(f"  - {doc_type}: {count}")

            # Check vector store size
            catalog_count = self.vector_store.document_catalog.count()
            content_count = self.vector_store.document_content.count()
            logger.info(f"\n💾 Vector Store:")
            logger.info(f"  - Catalog entries: {catalog_count}")
            logger.info(f"  - Content chunks: {content_count}")

        except Exception as e:
            logger.error(f"❌ Error generating stats: {e}", exc_info=True)


def main():
    """Main entry point"""
    # Setup logging first so we see output
    setup_logging(level='INFO')

    parser = argparse.ArgumentParser(
        description="Ingest business documents into Poolula Platform vector store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest all documents
  uv run python scripts/ingest_documents.py

  # Ingest specific directory
  uv run python scripts/ingest_documents.py --directory documents/formation

  # Ingest single file
  uv run python scripts/ingest_documents.py --file documents/formation/articles.pdf

  # Force rebuild (clear and re-ingest)
  uv run python scripts/ingest_documents.py --force

  # List ingested documents
  uv run python scripts/ingest_documents.py --list

Supported file types:
  - PDF (.pdf)
  - Word (.docx, .doc)
  - Text (.txt, .md)
        """
    )

    parser.add_argument('--file', type=str, help='Ingest a single file')
    parser.add_argument('--directory', type=str, help='Ingest all files in a directory')
    parser.add_argument('--force', action='store_true', help='Clear existing data and re-ingest')
    parser.add_argument('--list', action='store_true', help='List currently ingested documents')
    parser.add_argument('--stats', action='store_true', help='Show detailed ingestion statistics')

    args = parser.parse_args()

    # Initialize ingestor
    ingestor = DocumentIngestor(force_rebuild=args.force)

    try:
        if args.list:
            # List documents
            ingestor.list_ingested_documents()

        elif args.stats:
            # Show detailed statistics
            ingestor.show_document_stats()

        elif args.file:
            # Ingest single file
            file_path = Path(args.file)
            if not file_path.exists():
                logger.error(f"❌ File not found: {args.file}")
                sys.exit(1)

            result = ingestor.ingest_file(file_path)
            sys.exit(0 if result['success'] else 1)

        elif args.directory:
            # Ingest directory
            dir_path = Path(args.directory)
            summary = ingestor.ingest_directory(dir_path)

            logger.info(f"\n📊 Ingestion Summary:")
            logger.info(f"  - Files processed: {summary['total']}")
            logger.info(f"  - New documents: {summary['success'] - summary['skipped']}")
            logger.info(f"  - Skipped (duplicates): {summary['skipped']}")
            logger.info(f"  - Failed: {summary['failed']}")
            logger.info(f"  - Chunks added: {summary['chunks_added']}")

            sys.exit(0 if summary['failed'] == 0 else 1)

        else:
            # Default: ingest all documents
            summary = ingestor.ingest_all_documents()

            logger.info(f"\n📊 Ingestion Summary:")
            logger.info(f"  - Files processed: {summary['total']}")
            logger.info(f"  - New documents: {summary['success'] - summary['skipped']}")
            logger.info(f"  - Skipped (duplicates): {summary['skipped']}")
            logger.info(f"  - Failed: {summary['failed']}")
            logger.info(f"  - Chunks added: {summary['chunks_added']}")

            sys.exit(0 if summary['failed'] == 0 else 1)

    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
