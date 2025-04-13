"""JSON file-based storage implementation for emails."""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.models.email_data import EmailData
from src.config import PROCESSED_EMAILS_DIR
from src.storage.interface import EmailStorageInterface


# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


logger = logging.getLogger(__name__)


class JsonEmailStorage(EmailStorageInterface):
    """Implementation of email storage using JSON files."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        """Initialize JSON file storage.

        Args:
            storage_path: Optional custom path for storing email files
        """
        self.storage_path = storage_path or PROCESSED_EMAILS_DIR
        self._ensure_storage_path()

    def _ensure_storage_path(self) -> None:
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
                            if (
                                data_key not in email_data.get("extracted_data", {})
                                or email_data["extracted_data"][data_key] != data_value
                            ):
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


# Register this implementation with the factory
from src.storage.factory import EmailStorageFactory

def json_validator(config: Dict[str, Any]) -> None:
    if "storage_path" in config and not isinstance(config["storage_path"], str):
        raise ValueError("storage_path must be a string")

EmailStorageFactory.register("json", JsonEmailStorage, json_validator)
