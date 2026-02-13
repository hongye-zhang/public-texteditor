"""Dependency injection for LLM services."""
from typing import Generator

from fastapi import Depends, HTTPException

from app.features.llm.services.base import BaseLLMService
from app.features.llm.services.factory import LLMServiceFactory


def get_llm_service() -> Generator[BaseLLMService, None, None]:
    """
    Dependency that provides the LLM service instance.
    
    Yields:
        BaseLLMService: The LLM service instance
        
    Raises:
        HTTPException: If the LLM service cannot be initialized
    """
    try:
        # Get the default LLM service instance
        service = LLMServiceFactory.get_instance()
        yield service
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize LLM service: {str(e)}"
        )
    finally:
        # Clean up resources when the request is done
        # Note: In a real application, you might want to handle this differently
        # as it will close the service for all requests
        pass

# Alias for easier imports
LLMServiceDependency = Depends(get_llm_service)
