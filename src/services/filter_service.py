import os
import json
import logging
from typing import Dict, List, Optional, Protocol, Any, Type
from datetime import datetime

from src.models.email_filter import EmailFilter, EmailFilterCreate, EmailFilterUpdate
from src.models.email_data import EmailData, TransactionType
from src.config import EMAIL_STORAGE_PATH

logger = logging.getLogger(__name__)

FILTERS_FILE = os.path.join(EMAIL_STORAGE_PATH, "filters.json")


class FilterAdapter(Protocol):
    """Protocol for filter adapters that enhance email filter functionality."""

    def process(
        self, email: EmailData, extracted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process the email and update extracted data."""
        pass


class GenericTransactionAdapter:
    """Generic adapter for transaction emails that adds transaction direction information."""

    def __init__(self, owner_identifiers: Optional[List[str]] = None):
        """
        Initialize the adapter with owner identifiers.

        Args:
            owner_identifiers: List of strings that identify the owner in transaction fields
        """
        self.owner_identifiers = [str(id).upper() for id in (owner_identifiers or [])]

    def process(
        self, email: EmailData, extracted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Determines if a transaction is incoming or outgoing based on account information.

        Args:
            email: The email data object
            extracted_data: The data already extracted by filters

        Returns:
            Updated extracted data dictionary with transaction_type field
        """
        # Clone the extracted data to avoid modifying the original
        result = extracted_data.copy()

        # First, consolidate any fallback values
        for field in [
            "tipo_transaccion",
            "origen",
            "destino",
            "monto",
            "impuestos",
            "fecha_hora",
            "numero_referencia",
        ]:
            fallback_field = f"fallback_{field}"
            if fallback_field in extracted_data and field not in extracted_data:
                result[field] = extracted_data[fallback_field]

            # Remove fallback fields from the result
            if fallback_field in result:
                del result[fallback_field]

        # Check if we have the necessary fields to determine transaction type
        if "origen" not in result or "monto" not in result:
            return result

        # Get origin and destination fields
        origen = result.get("origen", "").upper()
        destino = result.get("destino", "").upper()

        # Default to unknown
        transaction_type = TransactionType.UNKNOWN.value

        # Check if any owner identifier is in the origin
        if any(owner_id in origen for owner_id in self.owner_identifiers):
            transaction_type = TransactionType.OUTGOING.value
        # Check if any owner identifier is in the destination
        elif any(owner_id in destino for owner_id in self.owner_identifiers):
            transaction_type = TransactionType.INCOMING.value

        result["transaction_type"] = transaction_type
        return result


class BanreservasTransactionAdapter(GenericTransactionAdapter):
    """Adapter for Banreservas transaction emails that adds transaction direction information."""

    def __init__(self) -> None:
        """Initialize with Banreservas-specific owner identifiers."""
        super().__init__(owner_identifiers=["STARLIN", "GIL CRUZ"])


# Registry of filter adapters by filter_id
FILTER_ADAPTERS: Dict[str, FilterAdapter] = {
    "banreservas_transacciones": BanreservasTransactionAdapter()
}


# Utility function to create a new adapter for any bank with custom identifiers
def create_transaction_adapter(
    owner_identifiers: List[str],
) -> GenericTransactionAdapter:
    """
    Creates a new generic transaction adapter with the given owner identifiers.

    Args:
        owner_identifiers: List of strings that identify the owner in transaction fields

    Returns:
        Configured GenericTransactionAdapter instance
    """
    return GenericTransactionAdapter(owner_identifiers=owner_identifiers)


class FilterService:
    def __init__(self) -> None:
        self.filters: Dict[str, EmailFilter] = {}
        self._ensure_storage_path()
        self._load_filters()

    def _ensure_storage_path(self) -> None:
        """Ensure the storage directory exists."""
        os.makedirs(EMAIL_STORAGE_PATH, exist_ok=True)

    def _load_filters(self) -> None:
        """Load filters from the JSON file."""
        if not os.path.exists(FILTERS_FILE):
            logger.info(
                f"Filters file not found at {FILTERS_FILE}, creating empty file"
            )
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

    def _save_filters(self) -> None:
        """Save filters to the JSON file."""
        try:
            # Handle both Pydantic v1 and v2
            filters_data = []
            for filter_obj in self.filters.values():
                if hasattr(filter_obj, "model_dump"):
                    filter_dict = filter_obj.model_dump()
                else:
                    filter_dict = filter_obj.dict()
                filters_data.append(filter_dict)

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

    def update_filter(
        self, filter_id: str, filter_data: EmailFilterUpdate
    ) -> Optional[EmailFilter]:
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
