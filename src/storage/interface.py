"""Interface for email storage backends."""

import abc
from typing import Dict, List, Optional, Any

from src.models.email_data import EmailData


class EmailStorageInterface(abc.ABC):
    """Abstract base class for email storage implementations."""

    @abc.abstractmethod
    def save_email(self, email_data: EmailData, use_chunks: bool = True) -> bool:
        """Save email data to storage.

        Args:
            email_data: The email data to save
            use_chunks: When True, save as individual files/records.
                       When False, append to a single file/collection.

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        pass

    @abc.abstractmethod
    def get_email(self, email_id: str) -> Optional[EmailData]:
        """Get email data by ID.

        Args:
            email_id: The ID of the email to retrieve

        Returns:
            Optional[EmailData]: The email data, or None if not found
        """
        pass

    @abc.abstractmethod
    def get_emails_by_filter(self, filter_id: str, limit: int = 100) -> List[EmailData]:
        """Get emails processed by a specific filter.

        Args:
            filter_id: The filter ID to match
            limit: Maximum number of emails to return

        Returns:
            List[EmailData]: List of matching emails
        """
        pass

    @abc.abstractmethod
    def delete_email(self, email_id: str) -> bool:
        """Delete an email by ID.

        Args:
            email_id: The ID of the email to delete

        Returns:
            bool: True if the email was deleted, False otherwise
        """
        pass

    @abc.abstractmethod
    def search_emails(self, query: Dict[str, Any], limit: int = 100) -> List[EmailData]:
        """Search emails by criteria.

        Args:
            query: Dictionary of search criteria
            limit: Maximum number of emails to return

        Returns:
            List[EmailData]: List of matching emails
        """
        pass
