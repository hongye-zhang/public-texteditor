"""Dependency injection modules for the API."""

from backend.app.features.llm.dependencies.llm import get_llm_service, LLMServiceDependency

__all__ = [
    'get_llm_service',
    'LLMServiceDependency',
]
