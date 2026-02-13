"""LLM Dependencies Module

This module provides dependency injection for LLM services.
"""

from app.features.llm.dependencies.llm import get_llm_service, LLMServiceDependency

# Export key components
__all__ = [
    'get_llm_service',
    'LLMServiceDependency'
]