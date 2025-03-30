from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.models.email_filter import EmailFilter, EmailFilterCreate, EmailFilterUpdate
from src.models.email_data import EmailData
from src.services.gmail_service import GmailService
from src.services.filter_service import FilterService
from src.storage import EmailStorageInterface, EmailStorageFactory
from src.config import get_storage_config
from src.utils import setup_logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MailScout API",
    description="API for filtering and extracting data from Gmail emails",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service dependencies
def get_gmail_service():
    service = GmailService()
    return service

def get_filter_service():
    service = FilterService()
    return service

def get_email_storage() -> EmailStorageInterface:
    """Get the configured email storage implementation."""
    storage_config = get_storage_config()
    storage_type = storage_config["type"]
    config = storage_config.get("config", {})
    
    return EmailStorageFactory.create_storage(storage_type, **config)


@app.get("/")
async def root():
    return {"message": "MailScout API is running"}


# Filter endpoints
@app.get("/filters", response_model=list[EmailFilter])
async def get_filters(
    active_only: bool = False,
    filter_service: FilterService = Depends(get_filter_service)
):
    """Get all email filters."""
    return filter_service.get_filters(active_only)


@app.get("/filters/{filter_id}", response_model=EmailFilter)
async def get_filter(
    filter_id: str,
    filter_service: FilterService = Depends(get_filter_service)
):
    """Get a specific email filter."""
    filter_obj = filter_service.get_filter(filter_id)
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    return filter_obj


@app.post("/filters", response_model=EmailFilter)
async def create_filter(
    filter_data: EmailFilterCreate,
    filter_service: FilterService = Depends(get_filter_service)
):
    """Create a new email filter."""
    return filter_service.create_filter(filter_data)


@app.put("/filters/{filter_id}", response_model=EmailFilter)
async def update_filter(
    filter_id: str,
    filter_data: EmailFilterUpdate,
    filter_service: FilterService = Depends(get_filter_service)
):
    """Update an existing email filter."""
    filter_obj = filter_service.update_filter(filter_id, filter_data)
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    return filter_obj


@app.delete("/filters/{filter_id}")
async def delete_filter(
    filter_id: str,
    filter_service: FilterService = Depends(get_filter_service)
):
    """Delete an email filter."""
    success = filter_service.delete_filter(filter_id)
    if not success:
        raise HTTPException(status_code=404, detail="Filter not found")
    return {"status": "success", "message": "Filter deleted"}


# Email processing endpoints
@app.post("/process/{filter_id}")
async def process_filter(
    filter_id: str,
    background_tasks: BackgroundTasks,
    max_results: int = 100,
    gmail_service: GmailService = Depends(get_gmail_service),
    filter_service: FilterService = Depends(get_filter_service),
    email_storage: EmailStorageInterface = Depends(get_email_storage)
):
    """Process a filter and fetch matching emails."""
    filter_obj = filter_service.get_filter(filter_id)

    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    
    if not filter_obj.is_active:
        raise HTTPException(status_code=400, detail="Filter is not active")
    
    # Process filter in background
    background_tasks.add_task(process_filter_background, filter_obj, max_results, gmail_service, email_storage)
    
    return {"status": "processing", "filter_id": filter_id}


async def process_filter_background(
    filter_obj: EmailFilter,
    max_results: int,
    gmail_service: GmailService,
    email_storage: EmailStorageInterface
):
    """Background task to process a filter."""
    try:
        emails = gmail_service.process_filter(filter_obj, max_results)
        
        # Save processed emails
        for email_data in emails:
            email_storage.save_email(email_data)
        
        logger.info(f"Processed filter {filter_obj.id}, saved {len(emails)} emails")
    except Exception as e:
        logger.error(f"Error processing filter {filter_obj.id}: {str(e)}")


@app.get("/emails/filter/{filter_id}", response_model=list[EmailData])
async def get_emails_by_filter(
    filter_id: str,
    limit: int = 100,
    email_storage: EmailStorageInterface = Depends(get_email_storage),
    filter_service: FilterService = Depends(get_filter_service)
):
    """Get emails processed by a specific filter."""
    filter_obj = filter_service.get_filter(filter_id)
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    
    emails = email_storage.get_emails_by_filter(filter_id, limit)
    return emails


@app.get("/emails/{email_id}", response_model=EmailData)
async def get_email(
    email_id: str,
    email_storage: EmailStorageInterface = Depends(get_email_storage)
):
    """Get a specific email by ID."""
    email_data = email_storage.get_email(email_id)
    if not email_data:
        raise HTTPException(status_code=404, detail="Email not found")
    return email_data


@app.delete("/emails/{email_id}")
async def delete_email(
    email_id: str,
    email_storage: EmailStorageInterface = Depends(get_email_storage)
):
    """Delete an email by ID."""
    success = email_storage.delete_email(email_id)
    if not success:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"status": "success", "message": "Email deleted"}