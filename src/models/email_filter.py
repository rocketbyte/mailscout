from typing import Dict, List, Optional, Union, Pattern
from pydantic import BaseModel, Field, validator
import re
import uuid
from datetime import datetime


class DataExtractionRule(BaseModel):
    name: str
    pattern: str
    _compiled_pattern: Optional[Pattern] = None
    group_name: Optional[str] = None
    
    def compile_pattern(self) -> None:
        """Compile the regex pattern for efficient reuse."""
        if not self._compiled_pattern:
            self._compiled_pattern = re.compile(self.pattern, re.MULTILINE | re.DOTALL)
    
    def extract_data(self, text: str) -> Optional[str]:
        """Extract data using the compiled pattern."""
        self.compile_pattern()
        match = self._compiled_pattern.search(text)
        if not match:
            return None
        
        if self.group_name and self.group_name in match.groupdict():
            return match.groupdict()[self.group_name]
        elif match.groups():
            return match.group(1)  # Default to first capture group
        else:
            return match.group(0)  # Whole match if no groups


class EmailFilter(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    subject_patterns: List[str] = Field(default_factory=list)
    from_patterns: List[str] = Field(default_factory=list)
    to_patterns: List[str] = Field(default_factory=list)
    content_patterns: List[str] = Field(default_factory=list)
    extraction_rules: List[DataExtractionRule] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EmailFilterCreate(BaseModel):
    name: str
    subject_patterns: List[str] = Field(default_factory=list)
    from_patterns: List[str] = Field(default_factory=list)
    to_patterns: List[str] = Field(default_factory=list)
    content_patterns: List[str] = Field(default_factory=list)
    extraction_rules: List[DataExtractionRule] = Field(default_factory=list)
    is_active: bool = True


class EmailFilterUpdate(BaseModel):
    name: Optional[str] = None
    subject_patterns: Optional[List[str]] = None
    from_patterns: Optional[List[str]] = None
    to_patterns: Optional[List[str]] = None
    content_patterns: Optional[List[str]] = None
    extraction_rules: Optional[List[DataExtractionRule]] = None
    is_active: Optional[bool] = None