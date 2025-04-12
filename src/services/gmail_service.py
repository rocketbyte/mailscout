import base64
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import email
from email.utils import parsedate_to_datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os
from dotenv import load_dotenv

from src.models.email_data import EmailData, EmailContent
from src.models.email_filter import EmailFilter
from src.config import EMAIL_STORAGE_PATH

# Load environment variables
load_dotenv()

GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN")

logger = logging.getLogger(__name__)


class GmailService:
    def __init__(self) -> None:
        self.service: Optional[Any] = None
        self._ensure_storage_path()

    def _ensure_storage_path(self) -> None:
        """Ensure the email storage directory exists."""
        os.makedirs(EMAIL_STORAGE_PATH, exist_ok=True)

    def authenticate(self) -> None:
        """Authenticate with Gmail API using refresh token."""
        if not all([GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN]):
            raise ValueError("Gmail API credentials not found in environment variables")

        try:
            credentials = Credentials(
                None,  # No token initially
                refresh_token=GMAIL_REFRESH_TOKEN,
                client_id=GMAIL_CLIENT_ID,
                client_secret=GMAIL_CLIENT_SECRET,
                token_uri="https://oauth2.googleapis.com/token",
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            )
            # Always refresh the token
            credentials.refresh(Request())

            self.service = build("gmail", "v1", credentials=credentials)
            logger.info("Authenticated with Gmail API")
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            if hasattr(e, "args") and len(e.args) > 1:
                logger.error(f"Error details: {e.args[1]}")
            raise

    def search_emails(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Search for emails using Gmail API query."""
        if not self.service:
            self.authenticate()
            
        if not self.service:  # If authentication failed
            logger.error("Gmail service not initialized")
            return []

        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} emails matching query: {query}")
            # Explicitly cast the result to the expected return type
            return [message for message in messages]
        except Exception as e:
            logger.error(f"Failed to search emails: {str(e)}")
            raise

    def get_email(self, message_id: str) -> Optional[EmailData]:
        """Get email details by message ID."""
        if not self.service:
            self.authenticate()

        if not self.service:  # If authentication failed
            logger.error("Gmail service not initialized")
            return None
            
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            return self._parse_email(message)
        except Exception as e:
            logger.error(f"Failed to get email with ID {message_id}: {str(e)}")
            return None

    def _decode_body(self, data: str) -> str:
        """Decode base64 encoded email body."""
        return base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8")

    def _parse_email(self, message: Dict[str, Any]) -> EmailData:
        """Parse Gmail message into EmailData model."""
        headers = {h["name"].lower(): h["value"] for h in message["payload"]["headers"]}

        # Get email content
        body: Dict[str, Optional[str]] = {"plain_text": None, "html": None}
        parts = [message["payload"]]

        while parts:
            part = parts.pop(0)

            if "parts" in part:
                parts.extend(part["parts"])

            if "body" in part and "data" in part["body"]:
                mime_type = part.get("mimeType", "")

                if mime_type == "text/plain":
                    body["plain_text"] = self._decode_body(part["body"]["data"])
                elif mime_type == "text/html":
                    body["html"] = self._decode_body(part["body"]["data"])

        # Check for attachments
        has_attachments = False
        attachments = []

        for part in message["payload"].get("parts", []):
            if part.get("filename") and part["filename"].strip():
                has_attachments = True
                attachments.append(part["filename"])

        # Parse date
        date_str = headers.get("date", "")
        date = datetime.now()
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
            except Exception:
                logger.warning(f"Failed to parse date: {date_str}")

        # Create EmailData object
        email_data = EmailData(
            message_id=message["id"],
            thread_id=message.get("threadId"),
            subject=headers.get("subject", "(No Subject)"),
            from_email=headers.get("from", ""),
            to_email=headers.get("to", "").split(","),
            cc_email=headers.get("cc", "").split(",") if "cc" in headers else [],
            bcc_email=headers.get("bcc", "").split(",") if "bcc" in headers else [],
            date=date,
            content=EmailContent(plain_text=body["plain_text"], html=body["html"]),
            labels=message.get("labelIds", []),
            has_attachments=has_attachments,
            attachments=attachments,
        )

        return email_data

    def build_query_from_filter(self, email_filter: EmailFilter) -> str:
        """Build Gmail search query from EmailFilter."""
        query_parts = []

        # Add subject patterns
        for pattern in email_filter.subject_patterns:
            query_parts.append(f"subject:({pattern})")

        # Add from patterns
        for pattern in email_filter.from_patterns:
            query_parts.append(f"from:({pattern})")

        # Add to patterns
        for pattern in email_filter.to_patterns:
            query_parts.append(f"to:({pattern})")

        # Combine query parts with OR
        if query_parts:
            return " OR ".join(query_parts)
        else:
            return ""

    def process_filter(
        self, email_filter: EmailFilter, max_results: int = 100
    ) -> List[EmailData]:
        """Process a filter and return matching emails with extracted data."""
        query = self.build_query_from_filter(email_filter)
        if not query:
            logger.warning(f"Filter {email_filter.id} has no query criteria")
            return []

        # Search for emails
        messages = self.search_emails(query, max_results)
        if not messages:
            return []

        # Process each email
        results = []
        for message in messages:
            email_data = self.get_email(message["id"])
            if not email_data:
                continue

            # Check content patterns if any
            if email_filter.content_patterns:
                content_match = False
                for pattern in email_filter.content_patterns:
                    # Check in plain text content
                    if (
                        email_data.content.plain_text
                        and pattern.lower() in email_data.content.plain_text.lower()
                    ):
                        content_match = True
                        break
                    # Check in HTML content
                    if (
                        email_data.content.html
                        and pattern.lower() in email_data.content.html.lower()
                    ):
                        content_match = True
                        break

                if not content_match:
                    continue

            # Extract data using rules
            extracted_data: Dict[str, str] = {}
            for rule in email_filter.extraction_rules:
                text_content = email_data.content.plain_text or ""
                html_content = email_data.content.html or ""
                extracted = rule.extract_data(text_content, html_content)
                if extracted:
                    extracted_data[rule.name] = extracted

            # Add extracted data and filter ID
            email_data.extracted_data = extracted_data
            email_data.filter_id = email_filter.id

            results.append(email_data)

        logger.info(f"Processed filter {email_filter.id}, found {len(results)} matches")
        return results
