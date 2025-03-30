import os
import pytest
import json
import tempfile
import shutil
from datetime import datetime

from src.models.email_data import EmailData, EmailContent
from src.services.email_storage import (
    EmailStorageInterface,
    JsonEmailStorage,
    MongoDBEmailStorage,
    EmailStorageFactory
)


@pytest.fixture
def sample_email_data():
    """Create a sample email for testing."""
    return EmailData(
        message_id="test123",
        subject="Test Email",
        from_email="sender@example.com",
        to_email=["recipient@example.com"],
        date=datetime.now(),
        content=EmailContent(plain_text="Test content", html="<p>Test content</p>"),
        filter_id="filter123"
    )


class TestJsonEmailStorage:
    """Tests for the JSON file email storage implementation."""
    
    @pytest.fixture
    def temp_storage_path(self):
        """Create a temporary directory for email storage."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def json_storage(self, temp_storage_path):
        """Create a JsonEmailStorage instance with a temporary directory."""
        storage = JsonEmailStorage()
        # Override the storage path for testing
        storage.storage_path = temp_storage_path
        return storage
    
    def test_save_and_get_email(self, json_storage, sample_email_data):
        """Test saving and retrieving an email."""
        # Save email
        assert json_storage.save_email(sample_email_data) is True
        
        # Verify file was created
        file_path = os.path.join(json_storage.storage_path, f"{sample_email_data.id}.json")
        assert os.path.exists(file_path)
        
        # Get email
        retrieved_email = json_storage.get_email(sample_email_data.id)
        assert retrieved_email is not None
        assert retrieved_email.message_id == sample_email_data.message_id
        assert retrieved_email.subject == sample_email_data.subject
        assert retrieved_email.from_email == sample_email_data.from_email
    
    def test_get_emails_by_filter(self, json_storage, sample_email_data):
        """Test getting emails by filter ID."""
        # Save email
        json_storage.save_email(sample_email_data)
        
        # Get emails by filter
        emails = json_storage.get_emails_by_filter(sample_email_data.filter_id)
        assert len(emails) == 1
        assert emails[0].id == sample_email_data.id
        
        # Test with non-existent filter
        emails = json_storage.get_emails_by_filter("non_existent_filter")
        assert len(emails) == 0
    
    def test_delete_email(self, json_storage, sample_email_data):
        """Test deleting an email."""
        # Save email
        json_storage.save_email(sample_email_data)
        
        # Delete email
        assert json_storage.delete_email(sample_email_data.id) is True
        
        # Verify file was deleted
        file_path = os.path.join(json_storage.storage_path, f"{sample_email_data.id}.json")
        assert not os.path.exists(file_path)
        
        # Test deleting non-existent email
        assert json_storage.delete_email("non_existent_id") is False
    
    def test_search_emails(self, json_storage, sample_email_data):
        """Test searching emails by criteria."""
        # Save email
        json_storage.save_email(sample_email_data)
        
        # Search by subject
        emails = json_storage.search_emails({"subject": "Test Email"})
        assert len(emails) == 1
        assert emails[0].id == sample_email_data.id
        
        # Search by from_email
        emails = json_storage.search_emails({"from_email": "sender@example.com"})
        assert len(emails) == 1
        
        # Search with non-matching criteria
        emails = json_storage.search_emails({"subject": "Non-existent"})
        assert len(emails) == 0
        
        # Search with multiple criteria
        emails = json_storage.search_emails({
            "subject": "Test Email",
            "from_email": "sender@example.com"
        })
        assert len(emails) == 1
        
        # Search with mixed criteria (matching and non-matching)
        emails = json_storage.search_emails({
            "subject": "Test Email",
            "from_email": "non-existent@example.com"
        })
        assert len(emails) == 0


class TestEmailStorageFactory:
    """Tests for the email storage factory."""
    
    def test_create_json_storage(self):
        """Test creating a JSON storage implementation."""
        storage = EmailStorageFactory.create_storage("json")
        assert isinstance(storage, JsonEmailStorage)
    
    def test_create_storage_invalid_type(self):
        """Test creating a storage with an invalid type."""
        with pytest.raises(ValueError):
            EmailStorageFactory.create_storage("invalid_type")
    
    def test_create_mongodb_storage_missing_params(self):
        """Test creating MongoDB storage with missing parameters."""
        with pytest.raises(ValueError):
            EmailStorageFactory.create_storage("mongodb")


# Skip MongoDB tests if pymongo is not installed
pymongo_available = True
try:
    import pymongo
except ImportError:
    pymongo_available = False

@pytest.mark.skipif(not pymongo_available, reason="pymongo not installed")
class TestMongoDBEmailStorage:
    """Tests for the MongoDB email storage implementation (requires MongoDB)."""
    
    # These tests require a running MongoDB instance
    # They are skipped by default - uncomment and adjust for real MongoDB testing
    
    """
    @pytest.fixture
    def mongo_storage(self):
        """Create a MongoDBEmailStorage instance with test database."""
        storage = MongoDBEmailStorage(
            connection_string="mongodb://localhost:27017",
            database_name="mailscout_test",
            collection_name="emails_test"
        )
        # Clear collection before each test
        storage.collection.delete_many({})
        yield storage
        # Clean up after tests
        storage.collection.delete_many({})
    
    def test_save_and_get_email(self, mongo_storage, sample_email_data):
        """Test saving and retrieving an email from MongoDB."""
        # Save email
        assert mongo_storage.save_email(sample_email_data) is True
        
        # Get email
        retrieved_email = mongo_storage.get_email(sample_email_data.id)
        assert retrieved_email is not None
        assert retrieved_email.message_id == sample_email_data.message_id
        assert retrieved_email.subject == sample_email_data.subject
    
    def test_get_emails_by_filter(self, mongo_storage, sample_email_data):
        """Test getting emails by filter ID from MongoDB."""
        # Save email
        mongo_storage.save_email(sample_email_data)
        
        # Get emails by filter
        emails = mongo_storage.get_emails_by_filter(sample_email_data.filter_id)
        assert len(emails) == 1
        assert emails[0].id == sample_email_data.id
    
    def test_delete_email(self, mongo_storage, sample_email_data):
        """Test deleting an email from MongoDB."""
        # Save email
        mongo_storage.save_email(sample_email_data)
        
        # Delete email
        assert mongo_storage.delete_email(sample_email_data.id) is True
        
        # Verify email was deleted
        retrieved_email = mongo_storage.get_email(sample_email_data.id)
        assert retrieved_email is None
    
    def test_search_emails(self, mongo_storage, sample_email_data):
        """Test searching emails in MongoDB."""
        # Save email
        mongo_storage.save_email(sample_email_data)
        
        # Search by subject
        emails = mongo_storage.search_emails({"subject": "Test Email"})
        assert len(emails) == 1
        assert emails[0].id == sample_email_data.id
        
        # Search with non-matching criteria
        emails = mongo_storage.search_emails({"subject": "Non-existent"})
        assert len(emails) == 0
    """