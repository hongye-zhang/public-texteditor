"""LLM Feature Module

This module provides LLM services and API endpoints for the application.
"""
# Import from new location for backward compatibility
from app.features.llm.services import BaseLLMService, OpenAIService, LLMServiceFactory
from app.features.llm.services.llm_service import stream_llm_response
from app.features.llm.services.base import BaseLLMService, LLMResponse
from app.features.llm.services.factory import LLMServiceFactory
from app.features.llm.services.llm_service import (
    stream_llm_response, 
    extract_actual_content,
    build_simple_insert_action
)
from app.features.llm.router import router
default_llm_service = LLMServiceFactory.create_service("openai")
# Export key components
__all__ = [
    'BaseLLMService',
    'LLMResponse',
    'OpenAIService',
    'LLMServiceFactory',
    'stream_llm_response',
    'default_llm_service',
    'extract_actual_content',
    'build_simple_insert_action',
    'router'
]



