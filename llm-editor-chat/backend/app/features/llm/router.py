"""API routes for the LLM feature.

This module provides API endpoints for interacting with LLM services.
"""
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.features.llm.services.base import BaseLLMService, LLMResponse
from app.features.llm.dependencies.llm import get_llm_service
from app.features.llm.services.article_outline import ArticleOutlineRequest, generate_article_outline, ArticleOutlineResponse

router = APIRouter(prefix="/llm", tags=["llm"])

class ChatRequest(BaseModel):
    """Request model for chat completion."""
    messages: List[Dict[str, str]]
    model: str = "gpt-4o"
    temperature: float = 0.7

@router.post("/chat")
async def chat_completion(
    request: ChatRequest,
    llm_service: BaseLLMService = Depends(get_llm_service)
) -> Dict[str, Any]:
    """
    Get a chat completion from the LLM service.
    
    This is a simple example of how to use the LLM service in a FastAPI route.
    For streaming responses, you would typically use a StreamingResponse.
    """
    try:
        # For demonstration, we'll collect all chunks into a single response
        full_response = ""
        async for chunk in llm_service.generate(
            messages=request.messages,
            model=request.model,
            temperature=request.temperature
        ):
            if isinstance(chunk, str):
                full_response += chunk
            else:  # It's an LLMResponse
                full_response = chunk.content
        
        return {
            "response": full_response,
            "model": request.model,
            "temperature": request.temperature
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )

@router.get("/models")
async def list_available_models(
    llm_service: BaseLLMService = Depends(get_llm_service)
) -> Dict[str, List[str]]:
    """List all available LLM models."""
    try:
        return {"models": llm_service.get_available_models()}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing models: {str(e)}"
        )

@router.post("/outline")
async def article_outline(request: ArticleOutlineRequest) -> ArticleOutlineResponse:
    """Generate an article outline based on the given parameters and reference materials."""
    return await generate_article_outline(request)
