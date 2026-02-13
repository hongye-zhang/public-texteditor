from typing import Optional, Dict, Any, List, AsyncGenerator
import json
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
import os

# Get API key
api_key = os.getenv("OPENAI_API_KEY")

class DocumentIntent(BaseModel):
    """Model for user document generation intent"""
    document_type: str = Field(
        description="Document type, can be 'ppt', 'letter', 'resume', 'article', etc."
    )
    confidence: float = Field(
        description="Confidence score of intent recognition, a float between 0-1",
        ge=0.0,
        le=1.0
    )
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional intent-related information, such as PPT topic, page count, etc."
    )

async def identify_document_intent(message: str, model: str = "gpt-4o", temperature: float = 0.0) -> DocumentIntent:
    """
    Use LangChain's PydanticOutputParser to identify document generation intent from user messages
    
    Args:
        message: Original user input text
        model: Language model name to use
        temperature: Temperature parameter for model generation diversity
        
    Returns:
        DocumentIntent: Identified document intent
    """
    # Create parser
    parser = PydanticOutputParser(pydantic_object=DocumentIntent)
    
    # System prompt
    system_prompt = """You are a document intent recognition assistant. Your task is to analyze user requests and determine what type of document they want to create.
Pay special attention to identifying the following document types:
1. PPT/slides/presentation - When the user wants to create a presentation
2. Letter/email - When the user wants to write a letter or email
3. Resume/CV - When the user wants to write a personal resume
4. Article/paper - When the user wants to write a general article or academic paper
5. Other - Other document types not belonging to the categories above

Based on the user's description, determine the most likely document type and provide your confidence level (a number between 0-1).
If the user explicitly mentions keywords like "PPT", "slides", "presentation", the document type should be identified as "ppt".

Your answer must be a valid JSON object containing the following fields:
- document_type: String identifier for the document type, such as "ppt", "letter", "resume", "article", etc.
- confidence: Your confidence in this classification, a float between 0-1
- additional_info: An optional object containing other relevant information extracted from the user request

For example, if the user says "Help me create a presentation about climate change for a speech", you should return:
```json
{
  "document_type": "ppt",
  "confidence": 0.95,
  "additional_info": {
    "topic": "climate change",
    "purpose": "speech"
  }
}
```
"""
    
    # Create format instructions
    format_instructions = """You must return a valid JSON object containing the following fields:
- document_type: String identifier for the document type, such as "ppt", "letter", "resume", "article", etc.
- confidence: Your confidence in this classification, a float between 0-1
- additional_info: An optional object containing other relevant information extracted from the user request"""
    
    # Create chat model
    chat = ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=temperature
    )
    
    # Create messages
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"{message}\n\n{format_instructions}")
    ]
    
    # Call the model
    response = await chat.ainvoke(messages)
    
    # Try to parse JSON response
    try:
        # Extract JSON from response
        content = response.content
        # Check if it's contained in a code block
        if "```json" in content and "```" in content:
            # Extract JSON from code block
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            # Might be a code block without specified language
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            # Assume the entire content is JSON
            json_str = content.strip()
            
        # Parse JSON
        data = json.loads(json_str)
        
        # Create DocumentIntent object
        return DocumentIntent(**data)
    except Exception as e:
        # If parsing fails, return default value
        print(f"Error parsing intent: {str(e)}")
        return DocumentIntent(
            document_type="unknown",
            confidence=0.0,
            additional_info={"error": str(e), "raw_response": response.content}
        )
