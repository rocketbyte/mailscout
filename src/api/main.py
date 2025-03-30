from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.models.email_filter import (
    EmailFilter, EmailFilterCreate, EmailFilterUpdate,
    WebhookConfig, WebhookConfigCreate, WebhookConfigUpdate, WebhookEventType
)
from src.models.email_data import EmailData
from src.services.gmail_service import GmailService
from src.services.filter_service import FilterService
from src.services.webhook_service import WebhookService
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

def get_webhook_service():
    service = WebhookService()
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
    email_storage: EmailStorageInterface = Depends(get_email_storage),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Process a filter and fetch matching emails."""
    filter_obj = filter_service.get_filter(filter_id)

    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    
    if not filter_obj.is_active:
        raise HTTPException(status_code=400, detail="Filter is not active")
    
    # Process filter in background
    background_tasks.add_task(
        process_filter_background, 
        filter_obj, 
        max_results, 
        gmail_service, 
        email_storage,
        webhook_service
    )
    
    return {"status": "processing", "filter_id": filter_id}


async def process_filter_background(
    filter_obj: EmailFilter,
    max_results: int,
    gmail_service: GmailService,
    email_storage: EmailStorageInterface,
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """Background task to process a filter."""
    try:
        emails = gmail_service.process_filter(filter_obj, max_results)
        
        # Save processed emails and send webhook notifications
        for email_data in emails:
            # Save email
            email_storage.save_email(email_data)
            
            # Send webhook notifications if webhooks are configured
            if filter_obj.webhooks:
                try:
                    await webhook_service.notify_webhooks(
                        filter_obj.webhooks,
                        WebhookEventType.EMAIL_PROCESSED,
                        email_data
                    )
                except Exception as webhook_err:
                    logger.error(f"Error sending webhook notifications: {str(webhook_err)}")
        
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


# Webhook endpoints
@app.get("/filters/{filter_id}/webhooks", response_model=list[WebhookConfig])
async def get_filter_webhooks(
    filter_id: str,
    filter_service: FilterService = Depends(get_filter_service)
):
    """Get all webhooks for a filter."""
    filter_obj = filter_service.get_filter(filter_id)
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    
    return filter_obj.webhooks


@app.post("/filters/{filter_id}/webhooks", response_model=WebhookConfig)
async def add_filter_webhook(
    filter_id: str,
    webhook_data: WebhookConfigCreate,
    filter_service: FilterService = Depends(get_filter_service)
):
    """Add a webhook to a filter."""
    filter_obj = filter_service.get_filter(filter_id)
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    
    # Create new webhook
    webhook = WebhookConfig(
        url=webhook_data.url,
        secret=webhook_data.secret,
        event_types=webhook_data.event_types,
        is_active=webhook_data.is_active,
        description=webhook_data.description
    )
    
    # Add webhook to filter
    filter_obj.webhooks.append(webhook)
    
    # Update filter
    updated_filter = filter_service.update_filter(
        filter_id, 
        EmailFilterUpdate(webhooks=[w for w in filter_obj.webhooks])
    )
    
    if not updated_filter:
        raise HTTPException(status_code=500, detail="Failed to update filter with new webhook")
    
    return webhook


@app.put("/filters/{filter_id}/webhooks/{webhook_id}", response_model=WebhookConfig)
async def update_filter_webhook(
    filter_id: str,
    webhook_id: str,
    webhook_data: WebhookConfigUpdate,
    filter_service: FilterService = Depends(get_filter_service)
):
    """Update a webhook for a filter."""
    filter_obj = filter_service.get_filter(filter_id)
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    
    # Find webhook
    webhook_index = None
    for i, webhook in enumerate(filter_obj.webhooks):
        if webhook.id == webhook_id:
            webhook_index = i
            break
    
    if webhook_index is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Update webhook fields
    webhook = filter_obj.webhooks[webhook_index]
    
    if webhook_data.url is not None:
        webhook.url = webhook_data.url
    if webhook_data.secret is not None:
        webhook.secret = webhook_data.secret
    if webhook_data.event_types is not None:
        webhook.event_types = webhook_data.event_types
    if webhook_data.is_active is not None:
        webhook.is_active = webhook_data.is_active
    if webhook_data.description is not None:
        webhook.description = webhook_data.description
    
    # Update filter with modified webhook
    filter_obj.webhooks[webhook_index] = webhook
    updated_filter = filter_service.update_filter(
        filter_id, 
        EmailFilterUpdate(webhooks=[w for w in filter_obj.webhooks])
    )
    
    if not updated_filter:
        raise HTTPException(status_code=500, detail="Failed to update filter webhook")
    
    return webhook


@app.delete("/filters/{filter_id}/webhooks/{webhook_id}")
async def delete_filter_webhook(
    filter_id: str,
    webhook_id: str,
    filter_service: FilterService = Depends(get_filter_service)
):
    """Delete a webhook from a filter."""
    filter_obj = filter_service.get_filter(filter_id)
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    
    # Remove webhook
    updated_webhooks = [w for w in filter_obj.webhooks if w.id != webhook_id]
    
    if len(updated_webhooks) == len(filter_obj.webhooks):
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Update filter with webhooks
    updated_filter = filter_service.update_filter(
        filter_id, 
        EmailFilterUpdate(webhooks=updated_webhooks)
    )
    
    if not updated_filter:
        raise HTTPException(status_code=500, detail="Failed to update filter webhooks")
    
    return {"status": "success", "message": "Webhook deleted"}