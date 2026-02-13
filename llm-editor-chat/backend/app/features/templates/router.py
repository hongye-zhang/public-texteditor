"""
FastAPI router for template endpoints.
This module provides API endpoints for template CRUD operations, search, and statistics.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID

from app.features.templates.models import (
    TemplateCreate, 
    TemplateUpdate, 
    TemplateResponse, 
    TemplateRatingCreate, 
    TemplateStats,
    TemplateSearchParams
)
from app.features.templates.service import template_service
from app.features.auth.dependencies import get_current_user, User

# Create router
router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/", response_model=List[TemplateResponse])
async def get_templates(
    category: Optional[str] = None,
    search: Optional[str] = None,
    visibility: str = "public",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get templates with optional filtering by category, search term, and visibility.
    If user is authenticated, includes their private templates.
    """
    search_params = TemplateSearchParams(
        category=category,
        search_term=search,
        visibility=visibility,
        limit=limit,
        offset=offset
    )
    
    # since there is not supabase, the following call may cause error,
    # comment it and return empty list for now
    """return await template_service.get_templates(
        params=search_params,
        user_id=str(current_user.id) if current_user else None
    )"""
    
    # Return empty list for now until supabase is configured
    return []


@router.post("/", response_model=TemplateResponse, status_code=201)
async def create_template(
    template: TemplateCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new template. User must be authenticated."""
    created_template = await template_service.create_template(
        template, 
        str(current_user.id)
    )
    
    if not created_template:
        raise HTTPException(status_code=500, detail="Failed to create template")
    
    return created_template


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get a specific template by ID.
    User must be authenticated for private templates they own.
    """
    template = await template_service.get_template_by_id(
        template_id, 
        user_id=str(current_user.id) if current_user else None
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    template_update: TemplateUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a template. User must be the template creator."""
    updated_template = await template_service.update_template(
        template_id, 
        template_update, 
        str(current_user.id)
    )
    
    if not updated_template:
        raise HTTPException(
            status_code=404, 
            detail="Template not found or you don't have permission to update it"
        )
    
    return updated_template


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Delete a template. User must be the template creator."""
    success = await template_service.delete_template(
        template_id, 
        str(current_user.id)
    )
    
    if not success:
        raise HTTPException(
            status_code=404, 
            detail="Template not found or you don't have permission to delete it"
        )
    
    return None


@router.post("/{template_id}/use", response_model=TemplateResponse)
async def use_template(
    template_id: UUID,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Record template usage and return the template.
    Anonymous usage is allowed for public templates.
    """
    template = await template_service.use_template(
        template_id,
        user_id=str(current_user.id) if current_user else None
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template


@router.post("/{template_id}/rate", status_code=201)
async def rate_template(
    template_id: UUID,
    rating: TemplateRatingCreate,
    current_user: User = Depends(get_current_user)
):
    """Rate a template. User must be authenticated."""
    success = await template_service.rate_template(
        template_id, 
        rating.rating, 
        rating.feedback, 
        str(current_user.id)
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"status": "success"}


@router.get("/{template_id}/stats", response_model=TemplateStats)
async def get_template_stats(
    template_id: UUID,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get usage statistics for a template."""
    stats = await template_service.get_template_stats(template_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Template stats not found")
    
    return stats


@router.get("/trending", response_model=List[TemplateResponse])
async def get_trending_templates(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(20, ge=1, le=50),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get trending templates based on recent usage."""
    return await template_service.get_trending_templates(
        days=days,
        limit=limit,
        user_id=str(current_user.id) if current_user else None
    )
