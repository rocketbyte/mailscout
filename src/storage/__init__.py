"""Storage module for MailScout.

This module contains implementations for different storage backends,
including JSON files and MongoDB.
"""

from src.storage.interface import EmailStorageInterface
from src.storage.factory import EmailStorageFactory
from src.storage.json_storage import JsonEmailStorage
from src.storage.mongodb_storage import MongoDBEmailStorage

# For backward compatibility with existing code
from src.storage.json_storage import JsonEmailStorage as EmailStorage

__all__ = [
    "EmailStorageInterface",
    "EmailStorageFactory",
    "JsonEmailStorage",
    "MongoDBEmailStorage",
    "EmailStorage",  # Legacy name
]