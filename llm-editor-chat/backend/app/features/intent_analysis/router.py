"""
Intent Analysis Router

This router provides endpoints for analyzing and identifying user intents.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.features.intent_analysis.services.intent_service import identify_document_intent, DocumentIntent
from app.features.intent_analysis.services.top_level_intent_service import identify_top_level_intent, TopLevelIntent
from app.features.intent_analysis.services.modify_existing_intent_service import identify_modify_existing_intent, ModifyExistingIntent
from app.features.intent_analysis.services.create_new_intent_service import identify_create_new_intent, CreateNewIntent
from app.features.intent_analysis.services.insert_image_intent_service import identify_insert_image_intent, InsertImageIntent

router = APIRouter(prefix="/intent", tags=["intent-analysis"])


class IntentRequest(BaseModel):
    """Intent analysis request model"""
    message: str
    context: Optional[str] = None


@router.post("/top-level", response_model=TopLevelIntent)
async def analyze_top_level_intent(request: IntentRequest):
    """
    Analyze the top-level intent of a user message
    """
    try:
        intent = await identify_top_level_intent(request.message)
        return intent
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing top-level intent: {str(e)}")


@router.post("/document", response_model=DocumentIntent)
async def analyze_document_intent(request: IntentRequest):
    """
    Analyze the document-related intent of a user message
    """
    try:
        intent = await identify_document_intent(request.message)
        return intent
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing document intent: {str(e)}")


@router.post("/modify", response_model=ModifyExistingIntent)
async def analyze_modify_intent(request: IntentRequest):
    """
    Analyze the modification intent of a user message
    """
    try:
        intent = await identify_modify_existing_intent(request.message)
        return intent
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing modification intent: {str(e)}")


@router.post("/create", response_model=CreateNewIntent)
async def analyze_create_intent(request: IntentRequest):
    """
    Analyze the creation intent of a user message
    """
    try:
        intent = await identify_create_new_intent(request.message)
        return intent
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing creation intent: {str(e)}")


@router.post("/insert-image", response_model=InsertImageIntent)
async def analyze_insert_image_intent(request: IntentRequest):
    """
    Analyze the image insertion intent of a user message
    """
    try:
        intent = await identify_insert_image_intent(request.message)
        return intent
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing image insertion intent: {str(e)}")
