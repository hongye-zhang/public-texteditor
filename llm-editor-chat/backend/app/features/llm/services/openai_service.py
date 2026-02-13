import logging
from typing import Dict, List, Optional, AsyncGenerator, Union, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

from .base import BaseLLMService, LLMResponse
from app.config import settings

logger = logging.getLogger(__name__)

class OpenAIService(BaseLLMService):
    """LLM service implementation using OpenAI's API via LangChain."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        default_temperature: Optional[float] = None,
        streaming: bool = True
    ):
        """
        Initialize the OpenAI service.
        
        Args:
            api_key: OpenAI API key. If None, will use settings.OPENAI_API_KEY
            default_model: Default model to use. If None, will use settings.llm_default_model
            default_temperature: Default temperature. If None, will use settings.llm_default_temperature
            streaming: Whether to enable streaming by default
        """
        self.api_key = api_key or settings.openai_api_key
        self.default_model = default_model or settings.llm_default_model
        self.default_temperature = (
            default_temperature 
            if default_temperature is not None 
            else settings.llm_default_temperature
        )
        self.streaming = streaming
        self._client = None
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
            
        logger.info(f"Initialized OpenAI service with model: {self.default_model}")
    
    def _get_client(self) -> ChatOpenAI:
        """Get or create the LangChain ChatOpenAI client."""
        if self._client is None:
            self._client = ChatOpenAI(
                api_key=self.api_key,
                model=self.default_model,
                temperature=self.default_temperature,
                streaming=self.streaming,
            )
        return self._client
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[BaseMessage]:
        """Convert message dicts to LangChain message objects."""
        langchain_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                logger.warning(f"Unknown message role: {role}, treating as user message")
                langchain_messages.append(HumanMessage(content=content))
                
        return langchain_messages
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        streaming: Optional[bool] = None,
        **kwargs
    ) -> AsyncGenerator[Union[str, LLMResponse], None]:
        """
        Generate a response using OpenAI's API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name to use. If None, uses the default model.
            temperature: Sampling temperature. If None, uses the default temperature.
            streaming: Whether to use streaming generation. If None, uses the instance default.
            **kwargs: Additional parameters to pass to the model.
            
        Yields:
            str: Token chunks during streaming
            LLMResponse: Final response with metadata when streaming is complete
        """
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature
        use_streaming = self.streaming if streaming is None else streaming
        
        # Create a new client with the specified parameters
        client = ChatOpenAI(
            api_key=self.api_key,
            model=model,
            temperature=temperature,
            streaming=use_streaming,
            **kwargs
        )
        
        # Convert messages to LangChain format
        langchain_messages = self._convert_messages(messages)
        
        # Buffer to accumulate full response
        full_response = ""
        
        try:
            if use_streaming:
                # Stream the response
                async for chunk in client.astream(langchain_messages, **kwargs):
                    if hasattr(chunk, 'content'):
                        content = chunk.content
                        if content:
                            full_response += content
                            yield content
                
                # Yield the complete response at the end
                if full_response:
                    yield LLMResponse(
                        content=full_response,
                        metadata={
                            "model": model,
                            "temperature": temperature,
                            "usage": {
                                "completion_tokens": len(full_response.split())
                            }
                        }
                    )
            else:
                # Non-streaming mode: get the full response at once
                response = await client.ainvoke(langchain_messages, **kwargs)
                if hasattr(response, 'content'):
                    full_response = response.content
                    # Yield the complete response
                    yield LLMResponse(
                        content=full_response,
                        metadata={
                            "model": model,
                            "temperature": temperature,
                            "usage": {
                                "completion_tokens": len(full_response.split())
                            }
                        }
                    )
                
        except Exception as e:
            logger.error(f"Error in OpenAI generation: {str(e)}", exc_info=True)
            raise
    
    async def generate_batch(
        self,
        messages_list: List[List[Dict[str, str]]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> List[AsyncGenerator[Union[str, LLMResponse], None]]:
        """
        Generate multiple responses in batch.
        
        Note: OpenAI's API doesn't support true batching in the free tier,
        so this is just a convenience wrapper around multiple generate calls.
        
        Args:
            messages_list: List of message lists, where each list is a conversation
            model: Model name to use. If None, uses the default model.
            temperature: Sampling temperature. If None, uses the default temperature.
            **kwargs: Additional parameters to pass to the model.
            
        Returns:
            List of async generators, one for each message list
        """
        return [
            self.generate(messages=messages, model=model, temperature=temperature, **kwargs)
            for messages in messages_list
        ]
    
    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models."""
        # Note: In a real implementation, you'd want to call the OpenAI API
        # to get the list of available models. For now, we'll return some common ones.
        return [
            "gpt-4o",
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-3.5-turbo",
        ]
    
    async def close(self):
        """Clean up resources."""
        if self._client is not None:
            # LangChain's ChatOpenAI doesn't have a close method, but we'll clean up anyways
            self._client = None
    
    def close_sync(self):
        """Synchronous version of close for use in __del__."""
        if self._client is not None:
            self._client = None
            
    def __del__(self):
        """Ensure resources are cleaned up when the object is garbage collected."""
        # Note: This is not guaranteed to be called in all Python implementations
        # and we can't call async methods in __del__, so we use the sync version
        self.close_sync()
