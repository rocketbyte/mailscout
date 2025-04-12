"""Webhook service for sending email notifications to subscribers."""

import logging
import json
import hmac
import hashlib
import httpx
import time
import asyncio
import datetime
from typing import Dict, Any, List, Optional, Union

from src.models.email_filter import WebhookConfig, WebhookEventType
from src.models.email_data import EmailData

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)


class WebhookService:
    """Service for managing and sending webhook notifications."""

    def __init__(self):
        self._retry_delay = 5  # seconds
        self._max_retries = 3

    def generate_signature(self, payload: str, secret: str) -> str:
        """
        Generate HMAC signature for webhook payload.

        Args:
            payload: JSON payload string
            secret: Webhook secret key

        Returns:
            str: HMAC-SHA256 signature as hex string
        """
        if not secret:
            return ""

        return hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    async def notify(
        self,
        webhook: WebhookConfig,
        event_type: WebhookEventType,
        data: Union[EmailData, Dict[str, Any]],
        retry: bool = True,
    ) -> bool:
        """
        Send notification to a webhook endpoint.

        Args:
            webhook: Webhook configuration
            event_type: Type of event that triggered the notification
            data: Data to send (EmailData or dict)
            retry: Whether to retry failed requests

        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not webhook.is_active:
            logger.debug(f"Webhook {webhook.id} is inactive, skipping notification")
            return False

        if (
            event_type not in webhook.event_types
            and WebhookEventType.ALL not in webhook.event_types
        ):
            logger.debug(
                f"Event type {event_type} not subscribed by webhook {webhook.id}"
            )
            return False

        # Prepare payload
        payload = {
            "event": event_type,
            "timestamp": int(time.time()),
            "data": data.model_dump() if hasattr(data, "model_dump") else data,
        }

        payload_json = json.dumps(payload, cls=DateTimeEncoder)
        signature = self.generate_signature(payload_json, webhook.secret or "")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MailScout-Webhook",
            "X-Webhook-Signature": signature,
        }

        # Send webhook request with retry
        attempt = 0
        while attempt <= (self._max_retries if retry else 0):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        str(webhook.url), content=payload_json, headers=headers
                    )

                    if 200 <= response.status_code < 300:
                        logger.info(
                            f"Webhook notification sent successfully to {webhook.url}"
                        )
                        return True
                    else:
                        logger.warning(
                            f"Webhook notification failed with status {response.status_code}: {response.text}"
                        )

                        if not retry or attempt >= self._max_retries:
                            return False
            except Exception as e:
                logger.error(f"Error sending webhook notification: {str(e)}")
                if not retry or attempt >= self._max_retries:
                    return False

            # Retry with exponential backoff
            attempt += 1
            if attempt <= self._max_retries:
                await asyncio.sleep(self._retry_delay * (2 ** (attempt - 1)))

        return False

    async def notify_webhooks(
        self,
        webhooks: List[WebhookConfig],
        event_type: WebhookEventType,
        data: Union[EmailData, Dict[str, Any]],
    ) -> Dict[str, bool]:
        """
        Send notifications to multiple webhooks in parallel.

        Args:
            webhooks: List of webhook configurations
            event_type: Type of event that triggered the notification
            data: Data to send

        Returns:
            Dict[str, bool]: Dictionary mapping webhook IDs to success status
        """
        if not webhooks:
            return {}

        results = {}
        tasks = []

        for webhook in webhooks:
            task = asyncio.create_task(self.notify(webhook, event_type, data))
            tasks.append((webhook.id, task))

        for webhook_id, task in tasks:
            success = await task
            results[webhook_id] = success

        return results
