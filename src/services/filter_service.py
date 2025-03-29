import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from src.models.email_filter import (
    EmailFilter, 
    EmailFilterCreate, 
    EmailFilterUpdate
)
from src.config import EMAIL_STORAGE_PATH

logger = logging.getLogger(__name__)

FILTERS_FILE = os.path.join(EMAIL_STORAGE_PATH, "filters.json")


class FilterService:
    def __init__(self):
        self.filters: Dict[str, EmailFilter] = {}
        self._ensure_storage_path()
        self._load_filters()
    
    def _ensure_storage_path(self):
        """Ensure the storage directory exists."""
        os.makedirs(EMAIL_STORAGE_PATH, exist_ok=True)
    
    def _load_filters(self):
        """Load filters from the JSON file."""
        if not os.path.exists(FILTERS_FILE):
            logger.info(f"Filters file not found at {FILTERS_FILE}, creating empty file")
            self._save_filters()
            return
        
        try:
            with open(FILTERS_FILE, "r") as f:
                filters_data = json.load(f)
            
            for filter_data in filters_data:
                email_filter = EmailFilter.parse_obj(filter_data)
                self.filters[email_filter.id] = email_filter
            
            logger.info(f"Loaded {len(self.filters)} filters from {FILTERS_FILE}")
        except Exception as e:
            logger.error(f"Failed to load filters: {str(e)}")
            self.filters = {}
    
    def _save_filters(self):
        """Save filters to the JSON file."""
        try:
            filters_data = [filter_obj.dict() for filter_obj in self.filters.values()]
            
            with open(FILTERS_FILE, "w") as f:
                json.dump(filters_data, f, indent=2)
            
            logger.info(f"Saved {len(self.filters)} filters to {FILTERS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save filters: {str(e)}")
    
    def get_filters(self, active_only: bool = False) -> List[EmailFilter]:
        """Get all filters, optionally filtered by active status."""
        if active_only:
            return [f for f in self.filters.values() if f.is_active]
        else:
            return list(self.filters.values())
    
    def get_filter(self, filter_id: str) -> Optional[EmailFilter]:
        """Get a filter by ID."""
        return self.filters.get(filter_id)
    
    def create_filter(self, filter_data: EmailFilterCreate) -> EmailFilter:
        """Create a new filter."""
        email_filter = EmailFilter(**filter_data.dict())
        self.filters[email_filter.id] = email_filter
        self._save_filters()
        return email_filter
    
    def update_filter(self, filter_id: str, filter_data: EmailFilterUpdate) -> Optional[EmailFilter]:
        """Update an existing filter."""
        if filter_id not in self.filters:
            return None
        
        current_filter = self.filters[filter_id]
        update_data = filter_data.dict(exclude_unset=True)
        
        for key, value in update_data.items():
            setattr(current_filter, key, value)
        
        # Update the timestamp
        current_filter.updated_at = datetime.now()
        self._save_filters()
        
        return current_filter
    
    def delete_filter(self, filter_id: str) -> bool:
        """Delete a filter by ID."""
        if filter_id not in self.filters:
            return False
        
        del self.filters[filter_id]
        self._save_filters()
        
        return True