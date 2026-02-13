"""
Pydantic models for the template feature.
These models define the data structures for templates, template ratings, and template statistics.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class TemplateBase(BaseModel):
    """Base model for template data."""
    name: str = Field(..., description="Name of the template")
    prompt: str = Field(..., description="Template prompt content")
    category: List[str] = Field(default=[], description="Categories for the template")
    required_fields: List[str] = Field(default=[], description="Required fields for the template")
    visibility: str = Field(default="private", description="Template visibility: private, public, or team")
    team_id: Optional[UUID] = Field(default=None, description="Team ID if template is team-specific")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the template")


class TemplateCreate(TemplateBase):
    """Model for creating a new template."""
    pass


class TemplateUpdate(BaseModel):
    """Model for updating an existing template."""
    name: Optional[str] = None
    prompt: Optional[str] = None
    category: Optional[List[str]] = None
    required_fields: Optional[List[str]] = None
    visibility: Optional[str] = None
    team_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class TemplateCreator(BaseModel):
    """Model for template creator information."""
    id: UUID
    email: Optional[str] = None
    display_name: Optional[str] = None


class TemplateResponse(TemplateBase):
    """Model for template response including all template data."""
    id: UUID
    creator_id: UUID
    creator: Optional[TemplateCreator] = None
    detected_variables: List[str] = Field(default=[], description="Variables detected in the template prompt")
    created_at: datetime
    updated_at: datetime
    
    # Stats (if available)
    use_count: Optional[int] = 0
    avg_rating: Optional[float] = 0
    rating_count: Optional[int] = 0
    
    class Config:
        orm_mode = True


class TemplateRatingCreate(BaseModel):
    """Model for creating a new template rating."""
    rating: int = Field(..., ge=1, le=5, description="Rating value from 1 to 5")
    feedback: Optional[str] = None
    
    @validator('rating')
    def rating_must_be_valid(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v


class TemplateStats(BaseModel):
    """Model for template statistics."""
    template_id: UUID
    use_count: int = 0
    success_rate: float = 0
    avg_rating: float = 0
    rating_count: int = 0
    last_used_at: Optional[datetime] = None


class TemplateSearchParams(BaseModel):
    """Model for template search parameters."""
    search_term: Optional[str] = None
    category: Optional[str] = None
    visibility: str = "public"
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
