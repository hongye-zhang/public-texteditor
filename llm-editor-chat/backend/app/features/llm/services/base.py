from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncGenerator, Union, Any


class LLMResponse:
    """Container for LLM response with metadata."""
    
    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize LLM response.
        
        Args:
            content: The generated text content
            metadata: Additional metadata about the response
        """
        self.content = content
        self.metadata = metadata or {}


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[Union[str, LLMResponse], None]:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name to use (optional, service can have default)
            temperature: Sampling temperature (0.0 to 1.0)
            **kwargs: Additional model-specific parameters
            
        Yields:
            Union[str, LLMResponse]: Chunks of the generated response or complete response
        """
        pass
    
    @abstractmethod
    async def generate_batch(
        self,
        messages_list: List[List[Dict[str, str]]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> List[AsyncGenerator[Union[str, LLMResponse], None]]:
        """
        Generate multiple responses in batch.
        
        Args:
            messages_list: List of message lists, each for one generation
            model: Model name to use
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Returns:
            List of async generators for each generation
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models.
        
        Returns:
            List of available model names
        """
        pass
    
    @abstractmethod
    async def close(self):
        """Clean up resources."""
        pass
