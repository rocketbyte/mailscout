"""Factory for creating storage implementations."""

from typing import Dict, Any, Type, Set, Callable, Optional

from src.storage.interface import EmailStorageInterface


class EmailStorageFactory:
    """Factory class to create storage implementations."""

    _implementations: Dict[str, Type[EmailStorageInterface]] = {}
    _validators: Dict[str, Callable[[Dict[str, Any]], None]] = {}

    @classmethod
    def register(
        cls, 
        storage_type: str, 
        implementation: Type[EmailStorageInterface],
        validator: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        """Register a storage implementation.

        Args:
            storage_type: The identifier for this storage type
            implementation: The implementation class
            validator: Optional function to validate constructor args
        """
        storage_type = storage_type.lower()
        cls._implementations[storage_type] = implementation
        
        if validator is not None:
            cls._validators[storage_type] = validator

    @classmethod
    def create_storage(cls, storage_type: str, **kwargs: Any) -> EmailStorageInterface:
        """Create and return a storage implementation based on type.

        Args:
            storage_type: The type of storage to create
            **kwargs: Additional arguments to pass to the implementation constructor

        Returns:
            EmailStorageInterface: An instance of the requested storage implementation

        Raises:
            ValueError: If the storage type is not supported or required arguments are missing
        """
        storage_type = storage_type.lower()

        if storage_type not in cls._implementations:
            raise ValueError(f"Unsupported storage type: {storage_type}")

        implementation = cls._implementations[storage_type]
        
        if storage_type in cls._validators:
            cls._validators[storage_type](kwargs)
            
        return implementation(**kwargs)
