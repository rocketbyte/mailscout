# Config package initialization
import os
import json
from pathlib import Path
from typing import Dict, Any

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = os.path.join(BASE_DIR, "data")
EMAIL_STORAGE_PATH = os.path.join(DATA_DIR, "emails")
PROCESSED_EMAILS_DIR = os.path.join(EMAIL_STORAGE_PATH, "processed_emails")

# Create directories if they don't exist
os.makedirs(EMAIL_STORAGE_PATH, exist_ok=True)
os.makedirs(PROCESSED_EMAILS_DIR, exist_ok=True)

# Default storage configuration
DEFAULT_STORAGE_CONFIG = {
    "type": "json",
    "config": {}
}

# MongoDB configuration (if used)
MONGODB_CONFIG = {
    "connection_string": os.environ.get("MONGODB_CONNECTION_STRING", "mongodb://localhost:27017"),
    "database_name": os.environ.get("MONGODB_DATABASE", "mailscout"),
    "collection_name": os.environ.get("MONGODB_COLLECTION", "emails")
}

# Load storage configuration from environment variables or default to file-based
STORAGE_TYPE = os.environ.get("MAILSCOUT_STORAGE_TYPE", "json").lower()

# Build the storage configuration
STORAGE_CONFIG = DEFAULT_STORAGE_CONFIG.copy()
STORAGE_CONFIG["type"] = STORAGE_TYPE

if STORAGE_TYPE == "mongodb":
    STORAGE_CONFIG["config"] = MONGODB_CONFIG

# Function to get storage configuration
def get_storage_config() -> Dict[str, Any]:
    """Get the configured storage type and configuration."""
    return STORAGE_CONFIG