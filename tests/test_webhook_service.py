"""Tests for the webhook service."""

import pytest
import asyncio
import json
import hashlib
import hmac
from typing import List
from unittest.mock import patch, AsyncMock, MagicMock

from src.models.email_filter import WebhookConfig, WebhookEventType
from src.models.email_data import EmailData
from src.services.webhook_service import WebhookService


@pytest.fixture
def webhook_service():
    """Return a webhook service instance for testing."""
    return WebhookService()


@pytest.fixture
def webhook_config():
    """Return a sample webhook configuration."""
    return WebhookConfig(
        url="https://example.com/webhook",
        secret="test_secret",
        event_types=[WebhookEventType.EMAIL_PROCESSED],
        is_active=True,
        description="Test webhook",
    )


@pytest.fixture
def email_data():
    """Return sample email data."""
    from datetime import datetime
    from src.models.email_data import EmailContent

    return EmailData(
        id="test-id",
        message_id="test-message-id",
        thread_id="test-thread-id",
        subject="Test Subject",
        from_email="sender@example.com",
        to_email=["recipient@example.com"],
        date=datetime.fromisoformat("2023-01-01T12:00:00"),
        content=EmailContent(plain_text="Test content", html="<p>Test content</p>"),
        extracted_data={"test_field": "test_value"},
        filter_id="test-filter-id",
    )


def test_generate_signature(webhook_service, email_data):
    """Test that the signature is correctly generated."""
    payload = json.dumps({"data": "test"})
    secret = "test_secret"

    signature = webhook_service.generate_signature(payload, secret)

    # Verify signature manually
    expected = hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    assert signature == expected


@pytest.mark.asyncio
async def test_notify_success(webhook_service, webhook_config, email_data):
    """Test successful webhook notification."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = await webhook_service.notify(
            webhook_config, WebhookEventType.EMAIL_PROCESSED, email_data
        )

        assert result is True
        mock_post.assert_called_once()

        # Check that correct URL was used
        args, kwargs = mock_post.call_args
        assert kwargs["content"]  # Payload should be included
        assert "https://example.com/webhook" in str(kwargs)


@pytest.mark.asyncio
async def test_notify_inactive_webhook(webhook_service, webhook_config, email_data):
    """Test notification to inactive webhook."""
    webhook_config.is_active = False

    with patch("httpx.AsyncClient.post") as mock_post:
        result = await webhook_service.notify(
            webhook_config, WebhookEventType.EMAIL_PROCESSED, email_data
        )

        assert result is False
        mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_notify_event_not_subscribed(webhook_service, webhook_config, email_data):
    """Test notification for event type not subscribed."""
    # Webhook only subscribed to EMAIL_PROCESSED, not FILTER_UPDATED
    result = await webhook_service.notify(
        webhook_config, WebhookEventType.FILTER_UPDATED, email_data, retry=False
    )

    assert result is False


@pytest.mark.asyncio
async def test_notify_retry_on_failure(webhook_service, webhook_config, email_data):
    """Test retry on webhook failure."""
    webhook_service._max_retries = 2
    webhook_service._retry_delay = 0.01  # Fast retry for tests

    with patch("httpx.AsyncClient.post") as mock_post, patch(
        "asyncio.sleep", return_value=None
    ) as mock_sleep:
        # First attempt fails, second succeeds
        mock_responses = [MagicMock(), MagicMock()]
        mock_responses[0].status_code = 500
        mock_responses[1].status_code = 200
        mock_post.side_effect = mock_responses

        result = await webhook_service.notify(
            webhook_config, WebhookEventType.EMAIL_PROCESSED, email_data
        )

        assert result is True
        assert mock_post.call_count == 2
        assert mock_sleep.called  # Should have slept between retries


@pytest.mark.asyncio
async def test_notify_webhooks(webhook_service, webhook_config, email_data):
    """Test notifying multiple webhooks."""
    webhooks = [
        webhook_config,
        WebhookConfig(
            url="https://example.org/webhook",
            event_types=[WebhookEventType.ALL],
            is_active=True,
        ),
    ]

    with patch.object(webhook_service, "notify", return_value=True) as mock_notify:
        results = await webhook_service.notify_webhooks(
            webhooks, WebhookEventType.EMAIL_PROCESSED, email_data
        )

        assert len(results) == 2
        assert all(results.values())  # All notifications successful
        assert mock_notify.call_count == 2
