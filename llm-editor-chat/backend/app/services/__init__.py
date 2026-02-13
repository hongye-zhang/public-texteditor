"""
Services Package

This package contains all service modules for the application.
This is a legacy package that is being gradually migrated to the feature-based architecture.
"""

# Import LLM service components
from .llm import (
    default_llm_service,
    BaseLLMService,
    OpenAIService,
    LLMServiceFactory,
    LLMResponse
)

# Export the default LLM service instance
llm_service = default_llm_service

# Export other service modules
# Avoid circular imports by not importing document_pipeline here
# Instead, we'll import it only when needed in the specific modules

__all__ = [
    'BaseLLMService',
    'OpenAIService',
    'LLMServiceFactory',
    'llm_service',
    'LLMResponse',
]

# Add compatibility imports for frontend
# This ensures that the frontend can still use the old import paths
# while we transition to the new feature-based architecture
from app.features.document_editing.services.document_pipeline_service import DocumentPipelineService
from app.features.document_editing.services.document_pipeline import DocumentPipeline, API_KEY
from app.features.llm.services.router import stream_llm_response

# These are not exported in __all__ to avoid circular imports
# but they are available for direct import
