from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import asyncio
import re
import os
from tempfile import NamedTemporaryFile

# Import shared service modules
from app.services.llm_service import stream_llm_response
from app.services.intent_service import identify_document_intent
from app.services.ppt_service import stream_ppt_generation

router = APIRouter(prefix="/chat", tags=["chat"])
# Removed StreamingCallbackHandler class, now using the version in llm_service

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    editor_content: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    file_path: Optional[str] = None  # Path to the uploaded file (if any)

@router.post("/upload-file")
async def upload_file(file: UploadFile = File(...)):
    """Upload file endpoint for handling file attachments"""
    try:
        # Create a temporary directory if it doesn't exist
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate a unique filename
        file_extension = os.path.splitext(file.filename)[1]
        temp_file_path = os.path.join(temp_dir, f"upload_{asyncio.current_task().get_name()}{file_extension}")
        
        # Save the uploaded file
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        return {"file_path": temp_file_path, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.post("/stream")
async def stream_chat(request: ChatRequest):
    """Streaming chat API endpoint"""
    
    async def generate():
        try:
            # Send initial "thinking" message
            yield f"data: {json.dumps({'type': 'thinking', 'content': 'Analyzing your request...'})}\n\n"
            
            # Use LangChain's PydanticOutputParser for intent recognition
            intent = await identify_document_intent(request.message)
            
            # Choose different processing paths based on intent
            if intent.document_type.lower() == "ppt" and intent.confidence > 0.6:
                # PPT generation path
                yield f"data: {json.dumps({'type': 'thinking', 'content': 'Detected PPT creation request. Using specialized PPT generator...'})}\n\n"
                
                # Use specialized PPT generation module
                async for event in stream_ppt_generation(
                    user_message=request.message,
                    editor_content=request.editor_content,
                    file_path=request.file_path
                ):
                    # Format event as SSE format
                    yield f"data: {json.dumps(event)}\n\n"
            else:
                # Other document generation path - use existing process
                system_prompt = """You are a document editing assistant. When a user provides a request, you need to:
1. Analyze the user's request and explain your thinking process
2. Generate content that meets the user's requirements
3. Finally, provide a clear action instruction to insert the content into the editor

When you need to insert content into the editor, use the following format:

[ACTION]
{
  "type": "insert",
  "payload": {
    "content": "content to insert"
  }
}
[/ACTION]
"""
                
                # Use shared service module to handle LLM streaming response
                async for event in stream_llm_response(
                    system_prompt=system_prompt,
                    user_message=request.message,
                    editor_content=request.editor_content
                ):
                    # Format event as SSE format
                    yield f"data: {json.dumps(event)}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error occurred: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
