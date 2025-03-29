import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.models.email_data import EmailData
from src.config import EMAIL_STORAGE_PATH, PROCESSED_EMAILS_DIR

logger = logging.getLogger(__name__)


class EmailStorage:
    def __init__(self):
        self.storage_path = PROCESSED_EMAILS_DIR
        self._ensure_storage_path()
    
    def _ensure_storage_path(self):
        """Ensure the storage directory exists."""
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _get_email_file_path(self, email_id: str) -> str:
        """Get file path for an email."""
        return os.path.join(self.storage_path, f"{email_id}.json")
    
    def save_email(self, email_data: EmailData) -> bool:
        """Save email data to storage."""
        try:
            file_path = self._get_email_file_path(email_data.id)
            
            with open(file_path, "w") as f:
                json.dump(email_data.dict(), f, indent=2)
            
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