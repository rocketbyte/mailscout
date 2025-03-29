from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class EmailContent(BaseModel):
    plain_text: Optional[str] = None
    html: Optional[str] = None


class EmailData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str
    thread_id: Optional[str] = None
    subject: str
    from_email: str
    to_email: List[str]
    cc_email: List[str] = Field(default_factory=list)
    bcc_email: List[str] = Field(default_factory=list)
    date: datetime
    content: EmailContent
    labels: List[str] = Field(default_factory=list)
    has_attachments: bool = False
    attachments: List[str] = Field(default_factory=list)
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    filter_id: Optional[str] = None
    processed_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }