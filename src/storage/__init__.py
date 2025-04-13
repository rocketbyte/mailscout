"""Storage module for MailScout.

This module contains implementations for different storage backends,
including JSON files and MongoDB.
"""

import os
import logging
from src.storage.interface import EmailStorageInterface
from src.storage.factory import EmailStorageFactory

# Get storage type from environment
STORAGE_TYPE = os.environ.get("MAILSCOUT_STORAGE_TYPE", "json").lower()
logger = logging.getLogger(__name__)

# Always import JSON storage as it's the default
from src.storage.json_storage import JsonEmailStorage

# For backward compatibility with existing code
from src.storage.json_storage import JsonEmailStorage as EmailStorage

# Only import MongoDB if it's the selected storage type
if STORAGE_TYPE == "mongodb":
    try:
        from src.storage.mongodb_storage import MongoDBEmailStorage
        logger.info("MongoDB storage module loaded")
    except ImportError as e:
        logger.warning(f"MongoDB storage selected but could not be imported: {str(e)}")
        logger.warning("Ensure pymongo is installed if using MongoDB storage")

__all__ = [
    "EmailStorageInterface",
    "EmailStorageFactory",
    "JsonEmailStorage",
    "EmailStorage",  # Legacy name
]

# Add MongoDBEmailStorage to __all__ only if it's imported
if STORAGE_TYPE == "mongodb" and "MongoDBEmailStorage" in globals():
    __all__.append("MongoDBEmailStorage")
