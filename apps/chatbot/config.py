import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('poolula_assistant.log', mode='a')
    ]
)

@dataclass
class Config:
    """Configuration settings for the RAG system"""
    # Anthropic API settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    
    # Embedding model settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Document processing settings (aligned with PRD requirements)
    # Approximate conversion: 1 token ≈ 4 characters for English text
    # Target: 600-1000 tokens = ~2400-4000 characters, using middle value of 800 tokens
    CHUNK_SIZE: int = 3200       # Size of text chunks (~800 tokens at 4 chars/token)
    CHUNK_OVERLAP: int = 400     # Characters to overlap between chunks (~100 tokens)
    MAX_RESULTS: int = 5         # Maximum search results to return
    MAX_HISTORY: int = 2         # Number of conversation messages to remember
    
    # Database paths
    CHROMA_PATH: str = "./chroma_db"  # ChromaDB storage location
    
    # Business document settings
    METADATA_CSV_PATH: str = "./metadata.csv"  # Path to document metadata CSV
    DOCS_PATH: str = "./docs"                  # Path to document folder
    
    # Caching settings
    CACHE_TTL_MINUTES: int = 5         # Query result cache time-to-live

config = Config()

# Create logger for configuration
logger = logging.getLogger(__name__)
logger.info(f"Configuration loaded - Model: {config.ANTHROPIC_MODEL}, Chunk Size: {config.CHUNK_SIZE}")

