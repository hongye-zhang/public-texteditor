"""
Template service for interacting with Supabase.
This module provides functions for template CRUD operations, search, and statistics.
"""
import re
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from app.core.supabase import get_supabase_client
from app.features.templates.models import (
    TemplateCreate, 
    TemplateUpdate, 
    TemplateResponse,
    TemplateStats,
    TemplateSearchParams
)


class TemplateService:
    """Service for template operations using Supabase."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def get_templates(
        self, 
        params: TemplateSearchParams,
        user_id: Optional[str] = None
    ) -> List[TemplateResponse]:
        """
        Get templates with optional filtering.
        If user_id is provided, includes their private templates.
        
        Args:
            params: Search parameters
            user_id: Optional user ID for including private templates
            
        Returns:
            List of templates matching the criteria
        """
        # Start building the query
        query = self.supabase.table("templates").select(
            "*, creator:profiles!creator_id(id, email, display_name)"
        )
        
        # Apply visibility filter
        if user_id:
            # Show public templates and user's own templates
            query = query.or_(f"visibility.eq.{params.visibility},creator_id.eq.{user_id}")
        else:
            # Only show public templates for anonymous users
            query = query.eq("visibility", params.visibility)
        
        # Apply category filter if provided
        if params.category:
            query = query.contains("category", [params.category])
        
        # Apply search if provided
        if params.search_term:
            # Use the search_templates RPC function if available
            # Otherwise fall back to basic filtering
            try:
                response = await self.supabase.rpc(
                    "search_templates",
                    {"search_term": params.search_term, "user_id": user_id or ""}
                ).execute()
                if not response.error:
                    return [TemplateResponse(**template) for template in response.data]
            except Exception as e:
                # Log error and fall back to basic filtering
                print(f"Error using search_templates RPC: {e}")
                # Basic title search fallback
                query = query.ilike("name", f"%{params.search_term}%")
        
        # Apply pagination
        query = query.range(params.offset, params.offset + params.limit - 1)
        
        # Execute query
        response = await query.execute()
        
        if response.error:
            # Log error and return empty list
            print(f"Error fetching templates: {response.error}")
            return []
        
        # Convert to TemplateResponse objects
        return [TemplateResponse(**template) for template in response.data]
    
    async def create_template(
        self, 
        template: TemplateCreate, 
        user_id: str
    ) -> Optional[TemplateResponse]:
        """
        Create a new template.
        
        Args:
            template: Template data
            user_id: Creator's user ID
            
        Returns:
            Created template or None if error
        """
        # Extract variables from prompt
        detected_variables = self._extract_variables(template.prompt)
        
        # Prepare template data
        template_data = template.dict()
        template_data.update({
            "creator_id": user_id,
            "detected_variables": detected_variables,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
        
        # Insert template
        response = await self.supabase.table("templates").insert(template_data).execute()
        
        if response.error:
            print(f"Error creating template: {response.error}")
            return None
        
        # Initialize stats
        template_id = response.data[0]["id"]
        await self.supabase.table("template_stats").insert({
            "template_id": template_id,
            "created_at": datetime.now().isoformat()
        }).execute()
        
        # Return created template
        return await self.get_template_by_id(template_id, user_id)
    
    async def get_template_by_id(
        self, 
        template_id: UUID, 
        user_id: Optional[str] = None
    ) -> Optional[TemplateResponse]:
        """
        Get a specific template by ID.
        User must be authenticated for private templates they own.
        
        Args:
            template_id: Template ID
            user_id: Optional user ID for accessing private templates
            
        Returns:
            Template if found and accessible, None otherwise
        """
        query = self.supabase.table("templates").select(
            "*, creator:profiles!creator_id(id, email, display_name)"
        ).eq("id", str(template_id))
        
        response = await query.execute()
        
        if response.error or not response.data:
            return None
        
        template = response.data[0]
        
        # Check if user has access to this template
        if template["visibility"] != "public" and template["creator_id"] != user_id:
            return None
        
        return TemplateResponse(**template)
    
    async def update_template(
        self, 
        template_id: UUID, 
        template_update: TemplateUpdate, 
        user_id: str
    ) -> Optional[TemplateResponse]:
        """
        Update a template. User must be the template creator.
        
        Args:
            template_id: Template ID
            template_update: Template update data
            user_id: User ID attempting the update
            
        Returns:
            Updated template if successful, None otherwise
        """
        # First check if user owns the template
        template = await self.get_template_by_id(template_id, user_id)
        if not template or template.creator_id != UUID(user_id):
            return None
        
        # Prepare update data
        update_data = template_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.now().isoformat()
        
        # If prompt is updated, re-extract variables
        if "prompt" in update_data:
            update_data["detected_variables"] = self._extract_variables(update_data["prompt"])
        
        # Update template
        response = await self.supabase.table("templates").update(
            update_data
        ).eq("id", str(template_id)).execute()
        
        if response.error:
            print(f"Error updating template: {response.error}")
            return None
        
        # Return updated template
        return await self.get_template_by_id(template_id, user_id)
    
    async def delete_template(
        self, 
        template_id: UUID, 
        user_id: str
    ) -> bool:
        """
        Delete a template. User must be the template creator.
        
        Args:
            template_id: Template ID
            user_id: User ID attempting the deletion
            
        Returns:
            True if deletion was successful, False otherwise
        """
        # First check if user owns the template
        template = await self.get_template_by_id(template_id, user_id)
        if not template or template.creator_id != UUID(user_id):
            return False
        
        # Delete template
        response = await self.supabase.table("templates").delete().eq(
            "id", str(template_id)
        ).execute()
        
        return not response.error
    
    async def use_template(
        self, 
        template_id: UUID, 
        user_id: Optional[str] = None
    ) -> Optional[TemplateResponse]:
        """
        Record template usage and return the template.
        Anonymous usage is allowed for public templates.
        
        Args:
            template_id: Template ID
            user_id: Optional user ID
            
        Returns:
            Template if found and accessible, None otherwise
        """
        # Get template
        template = await self.get_template_by_id(template_id, user_id)
        if not template:
            return None
        
        # Record usage
        usage_data = {
            "template_id": str(template_id),
            "used_at": datetime.now().isoformat()
        }
        
        if user_id:
            usage_data["user_id"] = user_id
        
        await self.supabase.table("template_usage").insert(usage_data).execute()
        
        # Update stats
        try:
            await self.supabase.rpc(
                "increment_use_count",
                {"template_id": str(template_id)}
            ).execute()
        except Exception as e:
            # Fall back to direct update if RPC fails
            print(f"Error using increment_use_count RPC: {e}")
            stats = await self.supabase.table("template_stats").select("*").eq(
                "template_id", str(template_id)
            ).execute()
            
            if not stats.error and stats.data:
                current_count = stats.data[0].get("use_count", 0)
                await self.supabase.table("template_stats").update({
                    "use_count": current_count + 1,
                    "last_used_at": datetime.now().isoformat()
                }).eq("template_id", str(template_id)).execute()
        
        return template
    
    async def rate_template(
        self, 
        template_id: UUID, 
        rating: int, 
        feedback: Optional[str], 
        user_id: str
    ) -> bool:
        """
        Rate a template. User must be authenticated.
        
        Args:
            template_id: Template ID
            rating: Rating value (1-5)
            feedback: Optional feedback text
            user_id: User ID submitting the rating
            
        Returns:
            True if rating was successful, False otherwise
        """
        # Check if template exists
        template = await self.get_template_by_id(template_id, user_id)
        if not template:
            return False
        
        # Upsert rating
        rating_data = {
            "template_id": str(template_id),
            "user_id": user_id,
            "rating": rating,
            "feedback": feedback,
            "created_at": datetime.now().isoformat()
        }
        
        response = await self.supabase.table("template_ratings").upsert(
            rating_data
        ).execute()
        
        if response.error:
            print(f"Error rating template: {response.error}")
            return False
        
        # Update stats
        try:
            await self.supabase.rpc(
                "update_template_rating_stats",
                {"template_id": str(template_id)}
            ).execute()
        except Exception as e:
            # Log error but consider rating successful
            print(f"Error updating rating stats: {e}")
        
        return True
    
    async def get_template_stats(
        self, 
        template_id: UUID
    ) -> Optional[TemplateStats]:
        """
        Get usage statistics for a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            Template statistics if found, None otherwise
        """
        response = await self.supabase.table("template_stats").select("*").eq(
            "template_id", str(template_id)
        ).execute()
        
        if response.error or not response.data:
            return None
        
        return TemplateStats(**response.data[0])
    
    async def get_trending_templates(
        self,
        days: int = 7,
        limit: int = 20,
        user_id: Optional[str] = None
    ) -> List[TemplateResponse]:
        """
        Get trending templates based on recent usage.
        
        Args:
            days: Number of days to consider for trending
            limit: Maximum number of templates to return
            user_id: Optional user ID for including private templates
            
        Returns:
            List of trending templates
        """
        try:
            # Try to use the get_trending_templates RPC function
            response = await self.supabase.rpc(
                "get_trending_templates",
                {
                    "days_back": days,
                    "result_limit": limit,
                    "user_id": user_id or ""
                }
            ).execute()
            
            if not response.error:
                return [TemplateResponse(**template) for template in response.data]
        except Exception as e:
            # Log error and fall back to basic query
            print(f"Error using get_trending_templates RPC: {e}")
        
        # Fallback: Get templates with highest use count
        query = self.supabase.table("templates").select(
            "*, creator:profiles!creator_id(id, email, display_name)"
        ).order("use_count", desc=True).limit(limit)
        
        # Filter by visibility
        if user_id:
            query = query.or_(f"visibility.eq.public,creator_id.eq.{user_id}")
        else:
            query = query.eq("visibility", "public")
        
        response = await query.execute()
        
        if response.error:
            print(f"Error fetching trending templates: {response.error}")
            return []
        
        return [TemplateResponse(**template) for template in response.data]
    
    def _extract_variables(self, prompt: str) -> List[str]:
        """
        Extract variables from a template prompt.
        Variables are identified by {{variable_name}} pattern.
        
        Args:
            prompt: Template prompt text
            
        Returns:
            List of variable names found in the prompt
        """
        # Match {{variable_name}} pattern
        matches = re.findall(r'{{([^{}]+)}}', prompt)
        # Remove duplicates and return
        return list(set(matches))


# Create a singleton instance
template_service = TemplateService()
