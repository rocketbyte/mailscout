import os
import json
import logging
import abc
from typing import Dict, List, Optional, Any, Protocol, Type
from datetime import datetime

from src.models.email_data import EmailData
from src.config import EMAIL_STORAGE_PATH, PROCESSED_EMAILS_DIR


# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

logger = logging.getLogger(__name__)


class EmailStorageInterface(abc.ABC):
    """Abstract base class for email storage implementations."""
    
    @abc.abstractmethod
    def save_email(self, email_data: EmailData) -> bool:
        """Save email data to storage."""
        pass
    
    @abc.abstractmethod
    def get_email(self, email_id: str) -> Optional[EmailData]:
        """Get email data by ID."""
        pass
    
    @abc.abstractmethod
    def get_emails_by_filter(self, filter_id: str, limit: int = 100) -> List[EmailData]:
        """Get emails processed by a specific filter."""
        pass
    
    @abc.abstractmethod
    def delete_email(self, email_id: str) -> bool:
        """Delete an email by ID."""
        pass
    
    @abc.abstractmethod
    def search_emails(self, query: Dict[str, Any], limit: int = 100) -> List[EmailData]:
        """Search emails by criteria."""
        pass


class JsonEmailStorage(EmailStorageInterface):
    """Implementation of email storage using JSON files."""
    
    def __init__(self):
        self.storage_path = PROCESSED_EMAILS_DIR
        self._ensure_storage_path()
    
    def _ensure_storage_path(self):
        """Ensure the storage directory exists."""
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _get_email_file_path(self, email_id: str) -> str:
        """Get file path for an email."""
        return os.path.join(self.storage_path, f"{email_id}.json")
    
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
        """Convert EmailData to dictionary."""
        # Handle both Pydantic v1 and v2
        if hasattr(email_data, "model_dump"):
            return email_data.model_dump()
        else:
            return email_data.dict()
    
    def save_email(self, email_data: EmailData) -> bool:
        """Save email data to storage."""
        try:
            # Apply filter adapters
            email_data = self._apply_filter_adapters(email_data)
            
            file_path = self._get_email_file_path(email_data.id)
            email_dict = self._to_dict(email_data)
                
            with open(file_path, "w") as f:
                json.dump(email_dict, f, indent=2, cls=DateTimeEncoder)
            
            logger.info(f"Saved email {email_data.id} to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save email {email_data.id}: {str(e)}")
            return False
    
    def get_email(self, email_id: str) -> Optional[EmailData]:
        """Get email data by ID."""
        file_path = self._get_email_file_path(email_id)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r") as f:
                email_data = json.load(f)
            
            return EmailData.parse_obj(email_data)
        except Exception as e:
            logger.error(f"Failed to load email {email_id}: {str(e)}")
            return None
    
    def get_emails_by_filter(self, filter_id: str, limit: int = 100) -> List[EmailData]:
        """Get emails processed by a specific filter."""
        emails = []
        count = 0
        
        try:
            for filename in os.listdir(self.storage_path):
                if not filename.endswith(".json"):
                    continue
                
                file_path = os.path.join(self.storage_path, filename)
                
                with open(file_path, "r") as f:
                    email_data = json.load(f)
                
                if email_data.get("filter_id") == filter_id:
                    emails.append(EmailData.parse_obj(email_data))
                    count += 1
                
                if count >= limit:
                    break
            
            return emails
        except Exception as e:
            logger.error(f"Failed to get emails by filter {filter_id}: {str(e)}")
            return []
    
    def delete_email(self, email_id: str) -> bool:
        """Delete an email by ID."""
        file_path = self._get_email_file_path(email_id)
        
        if not os.path.exists(file_path):
            return False
        
        try:
            os.remove(file_path)
            logger.info(f"Deleted email {email_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete email {email_id}: {str(e)}")
            return False
    
    def search_emails(self, query: Dict[str, Any], limit: int = 100) -> List[EmailData]:
        """Search emails by criteria."""
        emails = []
        count = 0
        
        try:
            for filename in os.listdir(self.storage_path):
                if not filename.endswith(".json"):
                    continue
                
                file_path = os.path.join(self.storage_path, filename)
                
                with open(file_path, "r") as f:
                    email_data = json.load(f)
                
                # Check if email matches query criteria
                match = True
                for key, value in query.items():
                    if key == "extracted_data":
                        # Special handling for extracted data
                        for data_key, data_value in value.items():
                            if data_key not in email_data.get("extracted_data", {}) or \
                               email_data["extracted_data"][data_key] != data_value:
                                match = False
                                break
                    elif key not in email_data or email_data[key] != value:
                        match = False
                        break
                
                if match:
                    emails.append(EmailData.parse_obj(email_data))
                    count += 1
                
                if count >= limit:
                    break
            
            return emails
        except Exception as e:
            logger.error(f"Failed to search emails: {str(e)}")
            return []


class MongoDBEmailStorage(EmailStorageInterface):
    """Implementation of email storage using MongoDB."""
    
    def __init__(self, connection_string: str, database_name: str, collection_name: str = "emails"):
        try:
            # Import here to make MongoDB optional
            import pymongo
            from pymongo import MongoClient
            
            self.client = MongoClient(connection_string)
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
            
            # Create indexes for common queries
            self.collection.create_index("id", unique=True)
            self.collection.create_index("filter_id")
            self.collection.create_index("message_id")
            
            logger.info(f"Connected to MongoDB database: {database_name}, collection: {collection_name}")
        except ImportError:
            logger.error("pymongo not installed. Please install with 'pip install pymongo'")
            raise ImportError("pymongo not installed. Please install with 'pip install pymongo'")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
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
        for key, value in email_dict.items():
            if isinstance(value, datetime):
                email_dict[key] = value.isoformat()
        
        return email_dict
    
    def save_email(self, email_data: EmailData) -> bool:
        """Save email data to MongoDB."""
        try:
            # Apply filter adapters
            email_data = self._apply_filter_adapters(email_data)
            
            email_dict = self._to_dict(email_data)
            
            # Use upsert to create or update based on ID
            result = self.collection.update_one(
                {"id": email_data.id},
                {"$set": email_dict},
                upsert=True
            )
            
            logger.info(f"Saved email {email_data.id} to MongoDB")
            return True
        except Exception as e:
            logger.error(f"Failed to save email {email_data.id} to MongoDB: {str(e)}")
            return False
    
    def get_email(self, email_id: str) -> Optional[EmailData]:
        """Get email data by ID from MongoDB."""
        try:
            email_data = self.collection.find_one({"id": email_id})
            
            if not email_data:
                return None
            
            # Remove MongoDB's _id field
            if "_id" in email_data:
                del email_data["_id"]
            
            return EmailData.parse_obj(email_data)
        except Exception as e:
            logger.error(f"Failed to load email {email_id} from MongoDB: {str(e)}")
            return None
    
    def get_emails_by_filter(self, filter_id: str, limit: int = 100) -> List[EmailData]:
        """Get emails processed by a specific filter from MongoDB."""
        emails = []
        
        try:
            cursor = self.collection.find({"filter_id": filter_id}).limit(limit)
            
            for email_data in cursor:
                # Remove MongoDB's _id field
                if "_id" in email_data:
                    del email_data["_id"]
                
                emails.append(EmailData.parse_obj(email_data))
            
            return emails
        except Exception as e:
            logger.error(f"Failed to get emails by filter {filter_id} from MongoDB: {str(e)}")
            return []
    
    def delete_email(self, email_id: str) -> bool:
        """Delete an email by ID from MongoDB."""
        try:
            result = self.collection.delete_one({"id": email_id})
            
            if result.deleted_count > 0:
                logger.info(f"Deleted email {email_id} from MongoDB")
                return True
            else:
                logger.warning(f"Email {email_id} not found in MongoDB")
                return False
        except Exception as e:
            logger.error(f"Failed to delete email {email_id} from MongoDB: {str(e)}")
            return False
    
    def search_emails(self, query: Dict[str, Any], limit: int = 100) -> List[EmailData]:
        """Search emails by criteria in MongoDB."""
        emails = []
        
        try:
            # Convert the query to MongoDB format
            mongo_query = {}
            
            for key, value in query.items():
                if key == "extracted_data":
                    # Special handling for extracted data
                    for data_key, data_value in value.items():
                        mongo_query[f"extracted_data.{data_key}"] = data_value
                else:
                    mongo_query[key] = value
            
            cursor = self.collection.find(mongo_query).limit(limit)
            
            for email_data in cursor:
                # Remove MongoDB's _id field
                if "_id" in email_data:
                    del email_data["_id"]
                
                emails.append(EmailData.parse_obj(email_data))
            
            return emails
        except Exception as e:
            logger.error(f"Failed to search emails in MongoDB: {str(e)}")
            return []


# Factory to create the appropriate storage implementation
class EmailStorageFactory:
    """Factory class to create storage implementations."""
    
    @staticmethod
    def create_storage(storage_type: str, **kwargs) -> EmailStorageInterface:
        """Create and return a storage implementation based on type."""
        if storage_type.lower() == "json":
            return JsonEmailStorage()
        elif storage_type.lower() == "mongodb":
            required_keys = ["connection_string", "database_name"]
            missing_keys = [key for key in required_keys if key not in kwargs]
            
            if missing_keys:
                raise ValueError(f"Missing required arguments for MongoDB storage: {', '.join(missing_keys)}")
            
            return MongoDBEmailStorage(
                connection_string=kwargs["connection_string"],
                database_name=kwargs["database_name"],
                collection_name=kwargs.get("collection_name", "emails")
            )
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")


# For backward compatibility
class EmailStorage(JsonEmailStorage):
    """Legacy class for backward compatibility."""
    pass