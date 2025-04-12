from typing import Dict, List, Optional, Union, Pattern, Literal
from pydantic import BaseModel, Field, validator, HttpUrl
import re
import uuid
from datetime import datetime
from bs4 import BeautifulSoup
from enum import Enum


class WebhookEventType(str, Enum):
    EMAIL_PROCESSED = "email_processed"
    FILTER_UPDATED = "filter_updated"
    ALL = "all"


class WebhookConfig(BaseModel):
    """Configuration for a webhook endpoint."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: HttpUrl
    secret: Optional[str] = None
    event_types: List[WebhookEventType] = Field(default=[WebhookEventType.ALL])
    is_active: bool = True
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class WebhookConfigCreate(BaseModel):
    """Schema for creating a webhook configuration."""

    url: HttpUrl
    secret: Optional[str] = None
    event_types: List[WebhookEventType] = Field(default=[WebhookEventType.ALL])
    is_active: bool = True
    description: Optional[str] = None


class WebhookConfigUpdate(BaseModel):
    """Schema for updating a webhook configuration."""

    url: Optional[HttpUrl] = None
    secret: Optional[str] = None
    event_types: Optional[List[WebhookEventType]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class DataExtractionRule(BaseModel):
    name: str
    pattern: str
    _compiled_pattern: Optional[Pattern] = None
    group_name: Optional[str] = None
    content_type: str = "text"  # Accepts "text", "html", "both", or "table"
    table_label: Optional[
        str
    ] = None  # For table extraction, the label to look for (e.g., "Monto")
    label_selector: str = "td.ic-form-label"  # CSS selector for table label cells
    value_selector: str = "td.ic-form-data"  # CSS selector for table value cells

    def compile_pattern(self) -> None:
        """Compile the regex pattern for efficient reuse."""
        if not self._compiled_pattern:
            self._compiled_pattern = re.compile(self.pattern, re.MULTILINE | re.DOTALL)

    def extract_from_table(self, html: str) -> Optional[str]:
        """
        Extract data from HTML tables by finding rows with matching labels.

        Args:
            html: HTML content containing tables

        Returns:
            Extracted value from the table cell or None if not found
        """
        if not html or not self.table_label:
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Find all label cells that might contain our label
            label_cells = soup.select(self.label_selector)

            for label_cell in label_cells:
                # Check if this cell contains our target label
                if self.table_label.lower() in label_cell.text.lower():
                    # Get the corresponding value cell (next sibling or parent's next child)
                    value_cell = label_cell.find_next(
                        self.value_selector.split(".")[-1]
                    )
                    if not value_cell and label_cell.parent:
                        value_cell = label_cell.parent.select_one(self.value_selector)

                    if value_cell:
                        # Extract and clean up the value
                        value = value_cell.text.strip()

                        # Apply regex pattern if specified to further refine extraction
                        if self.pattern and self._compiled_pattern:
                            self.compile_pattern()  # Ensure pattern is compiled
                            match = self._compiled_pattern.search(value)
                            if match and match.groups():
                                return match.group(1)  # Return first capture group as Optional[str]

                        # If no pattern or no match with groups, return entire value
                        return value  # Return as Optional[str]

            return None
        except Exception as e:
            print(f"Error extracting from table: {str(e)}")
            return None

    def extract_data(self, text: str, html: Optional[str] = None) -> Optional[str]:
        """
        Extract data using the compiled pattern from text or HTML content.

        Args:
            text: Plain text content to search
            html: HTML content to search (if content_type is 'html', 'both', or 'table')

        Returns:
            Extracted data or None if not found
        """
        # Special handling for table extraction
        if self.content_type == "table" and html:
            return self.extract_from_table(html)

        # Regular pattern-based extraction
        self.compile_pattern()
        if not self._compiled_pattern:
            return None

        # Determine which content to search based on content_type
        search_texts = []
        if self.content_type in ["text", "both"]:
            search_texts.append(text or "")
        if self.content_type in ["html", "both"] and html:
            search_texts.append(html)

        # Search in each content type
        for content in search_texts:
            match = self._compiled_pattern.search(content)
            if match:
                if self.group_name and self.group_name in match.groupdict():
                    return match.groupdict()[self.group_name]
                elif match.groups():
                    return match.group(1)  # Default to first capture group
                else:
                    return match.group(0)  # Whole match if no groups

        return None


class EmailFilter(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    subject_patterns: List[str] = Field(default_factory=list)
    from_patterns: List[str] = Field(default_factory=list)
    to_patterns: List[str] = Field(default_factory=list)
    content_patterns: List[str] = Field(default_factory=list)
    extraction_rules: List[DataExtractionRule] = Field(default_factory=list)
    webhooks: List[WebhookConfig] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EmailFilterCreate(BaseModel):
    name: str
    subject_patterns: List[str] = Field(default_factory=list)
    from_patterns: List[str] = Field(default_factory=list)
    to_patterns: List[str] = Field(default_factory=list)
    content_patterns: List[str] = Field(default_factory=list)
    extraction_rules: List[DataExtractionRule] = Field(default_factory=list)
    webhooks: List[WebhookConfigCreate] = Field(default_factory=list)
    is_active: bool = True


class EmailFilterUpdate(BaseModel):
    name: Optional[str] = None
    subject_patterns: Optional[List[str]] = None
    from_patterns: Optional[List[str]] = None
    to_patterns: Optional[List[str]] = None
    content_patterns: Optional[List[str]] = None
    extraction_rules: Optional[List[DataExtractionRule]] = None
    webhooks: Optional[List[WebhookConfigCreate]] = None
    is_active: Optional[bool] = None
