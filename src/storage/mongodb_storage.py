"""MongoDB storage implementation for emails."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.models.email_data import EmailData
from src.storage.interface import EmailStorageInterface


logger = logging.getLogger(__name__)

STORAGE_TYPE = 'mongodb'

class MongoDBEmailStorage(EmailStorageInterface):
    """Implementation of email storage using MongoDB."""

    def __init__(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str = "emails",
        bulk_collection_name: str = "emails_bulk",
    ) -> None:
        """Initialize MongoDB storage.

        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
            collection_name: Name of the collection to store individual emails
            bulk_collection_name: Name of the collection to store bulk emails

        Raises:
            ImportError: If pymongo is not installed
            ConnectionError: If connection to MongoDB fails
        """
        # Import here for type checking but don't instantiate yet
        try:
            from pymongo import MongoClient
            from pymongo.database import Database
            from pymongo.collection import Collection
            
            # Set instance variables first (without connecting)
            self.connection_string = connection_string
            self.database_name = database_name
            self.collection_name = collection_name
            self.bulk_collection_name = bulk_collection_name
            
            # Type annotations for lazy-initialized attributes
            self.client: Optional[MongoClient] = None
            self.db: Optional[Database] = None
            self.collection: Optional[Collection] = None  
            self.bulk_collection: Optional[Collection] = None
            
            # Lazy initialization - we'll connect only when needed
            self._initialized = False
        except ImportError:
            # Still define the attributes for type checking even if we can't import
            self.connection_string = connection_string
            self.database_name = database_name
            self.collection_name = collection_name
            self.bulk_collection_name = bulk_collection_name
            self.client = None
            self.db = None
            self.collection = None
            self.bulk_collection = None
            self._initialized = False
        
    def _ensure_connected(self) -> None:
        """Ensure connection to MongoDB is established.
        
        This is called before any operation that requires database access.
        """
        if self._initialized:
            return
            
        try:
            # Import here to make MongoDB optional
            import pymongo
            from pymongo import MongoClient

            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            self.bulk_collection = self.db[self.bulk_collection_name]

            # Create indexes for common queries
            self.collection.create_index("id", unique=True)
            self.collection.create_index("filter_id")
            self.collection.create_index("message_id")
            
            # Create indexes for bulk collection
            self.bulk_collection.create_index("id")
            self.bulk_collection.create_index("filter_id")
            self.bulk_collection.create_index("message_id")

            logger.info(
                f"Connected to MongoDB database: {self.database_name}, collections: {self.collection_name}, {self.bulk_collection_name}"
            )
            self._initialized = True
        except ImportError:
            logger.error(
                "pymongo not installed. Please install with 'pip install pymongo'"
            )
            raise ImportError(
                "pymongo not installed. Please install with 'pip install pymongo'"
            )
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise ConnectionError(f"Failed to connect to MongoDB: {str(e)}")

    def _apply_filter_adapters(self, email_data: EmailData) -> EmailData:
        """Apply filter adapters if applicable."""
        if email_data.filter_id:
            # Import inside function to avoid circular imports
            from src.services.filter_service import FILTER_ADAPTERS

            if email_data.filter_id in FILTER_ADAPTERS:
                adapter = FILTER_ADAPTERS[email_data.filter_id]
                enhanced_data = adapter.process(email_data, email_data.extracted_data)
                email_data.extracted_data = enhanced_data

        return email_data

    def _to_dict(self, email_data: EmailData) -> Dict[str, Any]:
        """Convert EmailData to dictionary with MongoDB-safe types."""
        # Handle both Pydantic v1 and v2
        if hasattr(email_data, "model_dump"):
            email_dict = email_data.model_dump()
        else:
            email_dict = email_data.dict()

        # Convert datetime objects to strings
        result_dict: Dict[str, Any] = {}
        for key, value in email_dict.items():
            if isinstance(value, datetime):
                result_dict[key] = value.isoformat()
            else:
                result_dict[key] = value

        return result_dict

    def save_email(self, email_data: EmailData, use_chunks: bool = True) -> bool:
        """Save email data to MongoDB."""
        try:
            # Ensure we are connected
            self._ensure_connected()
            
            # Apply filter adapters
            email_data = self._apply_filter_adapters(email_data)
            email_dict = self._to_dict(email_data)

            if use_chunks:
                # Save to individual collection
                result = self.collection.update_one(
                    {"id": email_data.id}, {"$set": email_dict}, upsert=True
                )
                logger.info(f"Saved email {email_data.id} to MongoDB collection {self.collection_name}")
            else:
                # Save to bulk collection
                # For MongoDB, we use a single document per email in the bulk collection
                # with upsert to update if it already exists
                result = self.bulk_collection.update_one(
                    {"id": email_data.id}, {"$set": email_dict}, upsert=True
                )
                logger.info(f"Saved email {email_data.id} to MongoDB bulk collection {self.bulk_collection_name}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to save email {email_data.id} to MongoDB: {str(e)}")
            return False

    def get_email(self, email_id: str) -> Optional[EmailData]:
        """Get email data by ID from MongoDB."""
        try:
            # Ensure we are connected
            self._ensure_connected()
            
            # First try the individual collection
            email_data = self.collection.find_one({"id": email_id})
            
            if not email_data:
                # If not found, try the bulk collection
                email_data = self.bulk_collection.find_one({"id": email_id})
                
                if not email_data:
                    return None

            # Remove MongoDB's _id field
            if "_id" in email_data:
                del email_data["_id"]

            # Explicitly return the typed result
            parsed_email: Optional[EmailData] = EmailData.parse_obj(email_data)
            return parsed_email
        except Exception as e:
            logger.error(f"Failed to load email {email_id} from MongoDB: {str(e)}")
            return None

    def get_emails_by_filter(self, filter_id: str, limit: int = 100) -> List[EmailData]:
        """Get emails processed by a specific filter from MongoDB."""
        emails = []
        count = 0

        try:
            # Ensure we are connected
            self._ensure_connected()
            
            # First get from individual collection
            cursor = self.collection.find({"filter_id": filter_id}).limit(limit)
            
            # Track email IDs we've already processed to avoid duplicates
            processed_ids = set()

            for email_data in cursor:
                # Remove MongoDB's _id field
                if "_id" in email_data:
                    del email_data["_id"]
                
                emails.append(EmailData.parse_obj(email_data))
                processed_ids.add(email_data["id"])
                count += 1
            
            # If we haven't reached the limit, also check bulk collection
            if count < limit:
                remaining = limit - count
                cursor = self.bulk_collection.find({"filter_id": filter_id}).limit(remaining)
                
                for email_data in cursor:
                    # Skip if we already have this email
                    if email_data["id"] in processed_ids:
                        continue
                        
                    # Remove MongoDB's _id field
                    if "_id" in email_data:
                        del email_data["_id"]
                    
                    emails.append(EmailData.parse_obj(email_data))
                    count += 1

            return emails
        except Exception as e:
            logger.error(
                f"Failed to get emails by filter {filter_id} from MongoDB: {str(e)}"
            )
            return []

    def delete_email(self, email_id: str) -> bool:
        """Delete an email by ID from MongoDB."""
        success = False
        
        try:
            # Ensure we are connected
            self._ensure_connected()
            
            # Try to delete from individual collection
            result = self.collection.delete_one({"id": email_id})
            if result.deleted_count > 0:
                logger.info(f"Deleted email {email_id} from MongoDB collection {self.collection_name}")
                success = True
            
            # Also try to delete from bulk collection
            result = self.bulk_collection.delete_one({"id": email_id})
            if result.deleted_count > 0:
                logger.info(f"Deleted email {email_id} from MongoDB bulk collection {self.bulk_collection_name}")
                success = True
                
            if not success:
                logger.warning(f"Email {email_id} not found in MongoDB")
                
            return success
        except Exception as e:
            logger.error(f"Failed to delete email {email_id} from MongoDB: {str(e)}")
            return False

    def search_emails(self, query: Dict[str, Any], limit: int = 100) -> List[EmailData]:
        """Search emails by criteria in MongoDB."""
        emails = []
        count = 0
        processed_ids = set()

        try:
            # Ensure we are connected
            self._ensure_connected()
            
            # Convert the query to MongoDB format
            mongo_query = {}

            for key, value in query.items():
                if key == "extracted_data":
                    # Special handling for extracted data
                    for data_key, data_value in value.items():
                        mongo_query[f"extracted_data.{data_key}"] = data_value
                else:
                    mongo_query[key] = value

            # First search in individual collection
            cursor = self.collection.find(mongo_query).limit(limit)

            for email_data in cursor:
                # Remove MongoDB's _id field
                if "_id" in email_data:
                    del email_data["_id"]

                emails.append(EmailData.parse_obj(email_data))
                processed_ids.add(email_data["id"])
                count += 1
            
            # If we haven't reached the limit, also search in bulk collection
            if count < limit:
                remaining = limit - count
                cursor = self.bulk_collection.find(mongo_query).limit(remaining)
                
                for email_data in cursor:
                    # Skip if we already have this email
                    if email_data["id"] in processed_ids:
                        continue
                        
                    # Remove MongoDB's _id field
                    if "_id" in email_data:
                        del email_data["_id"]

                    emails.append(EmailData.parse_obj(email_data))
                    count += 1

            return emails
        except Exception as e:
            logger.error(f"Failed to search emails in MongoDB: {str(e)}")
            return []


# Register this implementation with the factory
from src.storage.factory import EmailStorageFactory

def mongodb_validator(config: Dict[str, Any]) -> None:
    required_keys = ["connection_string", "database_name"]
    missing_keys = [key for key in required_keys if key not in config]
    
    if missing_keys:
        raise ValueError(
            f"Missing required arguments for MongoDB storage: {', '.join(missing_keys)}"
        )
    
    # Validate optional parameters
    if "bulk_collection_name" in config and not isinstance(config["bulk_collection_name"], str):
        raise ValueError("bulk_collection_name must be a string")

EmailStorageFactory.register(STORAGE_TYPE, MongoDBEmailStorage, mongodb_validator)
