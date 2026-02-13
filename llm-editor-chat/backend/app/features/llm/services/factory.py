import logging
from typing import Optional, Type, Dict, Any

from .base import BaseLLMService
from .openai_service import OpenAIService
from app.config import settings

logger = logging.getLogger(__name__)

class LLMServiceFactory:
    """Factory for creating and managing LLM service instances."""
    
    _instance: Optional[BaseLLMService] = None
    _service_registry: Dict[str, Type[BaseLLMService]] = {
        "openai": OpenAIService,
        # Add other service types here as they're implemented
    }
    
    @classmethod
    def register_service(
        cls, 
        service_type: str, 
        service_class: Type[BaseLLMService]
    ) -> None:
        """
        Register a new LLM service type.
        
        Args:
            service_type: Unique identifier for the service type (e.g., 'openai')
            service_class: The service class to register
        """
        cls._service_registry[service_type] = service_class
        logger.info(f"Registered LLM service type: {service_type}")
    
    @classmethod
    def create_service(
        cls,
        service_type: str = "openai",
        **kwargs
    ) -> BaseLLMService:
        """
        Create a new instance of the specified LLM service.
        
        Args:
            service_type: Type of service to create (default: 'openai')
            **kwargs: Additional arguments to pass to the service constructor
            
        Returns:
            BaseLLMService: New instance of the requested service
            
        Raises:
            ValueError: If the specified service type is not registered
        """
        if service_type not in cls._service_registry:
            raise ValueError(
                f"Unknown LLM service type: {service_type}. "
                f"Available types: {list(cls._service_registry.keys())}"
            )
            
        service_class = cls._service_registry[service_type]
        logger.info(f"Creating new {service_type} LLM service instance")
        return service_class(**kwargs)
    
    @classmethod
    def get_instance(
        cls, 
        service_type: str = "openai",
        force_new: bool = False,
        **kwargs
    ) -> BaseLLMService:
        """
        Get or create the singleton LLM service instance.
        
        Args:
            service_type: Type of service to get/create (default: 'openai')
            force_new: If True, always create a new instance
            **kwargs: Additional arguments to pass to the service constructor
            
        Returns:
            BaseLLMService: The singleton service instance
        """
        if force_new or cls._instance is None:
            # Set default API key if not provided
            if 'api_key' not in kwargs:
                kwargs['api_key'] = settings.openai_api_key
                
            cls._instance = cls.create_service(service_type, **kwargs)
            
        return cls._instance
    
    @classmethod
    def set_instance(cls, instance: BaseLLMService) -> None:
        """
        Set the LLM service instance (for testing or dependency injection).
        
        Args:
            instance: The service instance to use
        """
        cls._instance = instance
        logger.info("Manually set LLM service instance")
    
    @classmethod
    async def close(cls) -> None:
        """Close the current LLM service instance if it exists."""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None
            logger.info("Closed LLM service instance")


# Create a default instance for convenience
default_llm_service = LLMServiceFactory.get_instance()
