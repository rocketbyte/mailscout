"""Factory for creating storage implementations."""

from typing import Dict, Any, Type

from src.storage.interface import EmailStorageInterface


class EmailStorageFactory:
    """Factory class to create storage implementations."""
    
    _implementations = {}
    
    @classmethod
    def register(cls, storage_type: str, implementation: Type[EmailStorageInterface]):
        """Register a storage implementation.
        
        Args:
            storage_type: The identifier for this storage type
            implementation: The implementation class
        """
        cls._implementations[storage_type.lower()] = implementation
    
    @classmethod
    def create_storage(cls, storage_type: str, **kwargs) -> EmailStorageInterface:
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
        
        # Handle specific implementation requirements
        if storage_type == "mongodb":
            required_keys = ["connection_string", "database_name"]
            missing_keys = [key for key in required_keys if key not in kwargs]
            
            if missing_keys:
                raise ValueError(f"Missing required arguments for MongoDB storage: {', '.join(missing_keys)}")
        
        return implementation(**kwargs)