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
from core.logging_config import get_logger

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

    def ingest_file(self, file_path: Path) -> bool:
        """
        Ingest a single document file

        Args:
            file_path: Path to document file

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Processing: {file_path}")

            # Check if document already exists by content hash
            # (This would require computing hash first, skipping for now)

            # Get metadata for the file
            metadata = self.metadata_manager.get_metadata_for_file(str(file_path))

            # Process the document
            document, chunks = self.doc_processor.process_business_document(
                str(file_path),
                metadata
            )

            logger.info(f"  - Extracted {len(chunks)} chunks")

            # Add to vector store
            self.vector_store.add_document_metadata(document)
            self.vector_store.add_document_content(chunks)

            logger.info(f"  ✅ Successfully ingested: {file_path.name}")
            return True

        except Exception as e:
            logger.error(f"  ❌ Error processing {file_path}: {e}", exc_info=True)
            return False

    def ingest_directory(self, directory_path: Path, recursive: bool = True) -> dict:
        """
        Ingest all supported files from a directory

        Args:
            directory_path: Path to directory
            recursive: Whether to process subdirectories

        Returns:
            Summary dict with counts
        """
        if not directory_path.exists():
            logger.error(f"❌ Directory not found: {directory_path}")
            return {"total": 0, "success": 0, "failed": 0}

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
            return {"total": 0, "success": 0, "failed": 0}

        logger.info(f"Found {len(files_to_process)} files to process")

        # Process each file
        success_count = 0
        for file_path in files_to_process:
            if self.ingest_file(file_path):
                success_count += 1

        summary = {
            "total": len(files_to_process),
            "success": success_count,
            "failed": len(files_to_process) - success_count
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


def main():
    """Main entry point"""
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

    args = parser.parse_args()

    # Initialize ingestor
    ingestor = DocumentIngestor(force_rebuild=args.force)

    try:
        if args.list:
            # List documents
            ingestor.list_ingested_documents()

        elif args.file:
            # Ingest single file
            file_path = Path(args.file)
            if not file_path.exists():
                logger.error(f"❌ File not found: {args.file}")
                sys.exit(1)

            success = ingestor.ingest_file(file_path)
            sys.exit(0 if success else 1)

        elif args.directory:
            # Ingest directory
            dir_path = Path(args.directory)
            summary = ingestor.ingest_directory(dir_path)

            logger.info(f"\n📊 Ingestion Summary:")
            logger.info(f"  - Files processed: {summary['total']}")
            logger.info(f"  - Successful: {summary['success']}")
            logger.info(f"  - Failed: {summary['failed']}")

            sys.exit(0 if summary['failed'] == 0 else 1)

        else:
            # Default: ingest all documents
            summary = ingestor.ingest_all_documents()

            logger.info(f"\n📊 Ingestion Summary:")
            logger.info(f"  - Files processed: {summary['total']}")
            logger.info(f"  - Successful: {summary['success']}")
            logger.info(f"  - Failed: {summary['failed']}")

            sys.exit(0 if summary['failed'] == 0 else 1)

    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
