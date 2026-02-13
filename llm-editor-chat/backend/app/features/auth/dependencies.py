"""
Authentication dependencies for FastAPI.
This module provides dependencies for user authentication and authorization.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from pydantic import BaseModel
from uuid import UUID

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)

class User(BaseModel):
    """User model for authentication and authorization."""
    id: UUID
    email: str
    name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
    """
    Get the current authenticated user based on the provided token.
    
    This is a simplified implementation for development purposes.
    In production, this would validate the token and retrieve the user from a database.
    
    Args:
        token: The OAuth2 token from the request
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not token:
        return None
        
    # For development, return a mock user
    # In production, this would validate the JWT token and retrieve the user
    try:
        # Mock user for development
        return User(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            email="dev@example.com",
            name="Development User",
            is_active=True
        )
    except Exception:
        return None

async def get_required_user(current_user: Optional[User] = Depends(get_current_user)) -> User:
    """
    Get the current user, raising an exception if not authenticated.
    
    Args:
        current_user: The current user from get_current_user
        
    Returns:
        User object
        
    Raises:
        HTTPException: If no authenticated user
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user
