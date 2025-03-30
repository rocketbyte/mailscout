"""
This module is deprecated and will be removed in a future version.
Import from src.storage instead.
"""

import logging
from typing import Dict, Any

from src.storage import (
    EmailStorageInterface,
    JsonEmailStorage,
    MongoDBEmailStorage,
    EmailStorageFactory,
    EmailStorage as _EmailStorage
)

logger = logging.getLogger(__name__)
logger.warning(
    "The 'src.services.email_storage' module is deprecated. "
    "Please import from 'src.storage' instead."
)

# Re-export for backward compatibility
EmailStorageInterface = EmailStorageInterface
JsonEmailStorage = JsonEmailStorage
MongoDBEmailStorage = MongoDBEmailStorage
EmailStorageFactory = EmailStorageFactory
EmailStorage = _EmailStorage