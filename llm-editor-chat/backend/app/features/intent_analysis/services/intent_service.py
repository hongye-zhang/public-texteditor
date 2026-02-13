from typing import Optional, Dict, Any, List, AsyncGenerator
import json
import logging
from pydantic import BaseModel, Field
from app.utils.llm_utils import generate_text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocumentIntent(BaseModel):
    """Model for user document generation intent (second-level intent)"""
    document_type: str = Field(
        description="Document type, can be 'ppt', 'letter', 'resume', 'article', 'section_edit', etc."
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
    # 直接使用提示和手动JSON解析，不需要专门的parser
    
    # System prompt
    system_prompt = """You are a document intent recognition assistant. Your task is to analyze user requests and determine what type of document they want to create or edit.
Pay special attention to identifying the following document types and actions:
1. PPT/slides/presentation - When the user wants to create a presentation
2. Letter/email - When the user wants to write a letter or email
3. Resume/CV - When the user wants to write a personal resume
4. Article/paper - When the user wants to write a general article or academic paper
5. section_edit - When the user wants to edit a specific section of a document without specifying which section (e.g., "add a paragraph about X", "improve the introduction", "fix the grammar")
6. Other - Other document types not belonging to the categories above

The "section_edit" type is special - use it when the user is asking to edit or modify content but doesn't specify exactly which section. This will trigger intelligent section finding.

Based on the user's description, determine the most likely document type and provide your confidence level (a number between 0-1).
If the user explicitly mentions keywords like "PPT", "slides", "presentation", the document type should be identified as "ppt".
If the user uses editing terms like "edit", "change", "modify", "update", "revise", "rewrite", "add", "insert", "improve", etc. without specifying a section, use "section_edit".

Your answer must be a valid JSON object containing the following fields:
- document_type: String identifier for the document type, such as "ppt", "letter", "resume", "article", "section_edit", etc.
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

If the user says "Add a paragraph about renewable energy", you should return:
```json
{
  "document_type": "section_edit",
  "confidence": 0.9,
  "additional_info": {
    "edit_type": "add",
    "topic": "renewable energy"
  }
}
```
"""
    
    # Create format instructions
    format_instructions = """You must return a valid JSON object containing the following fields:
- document_type: String identifier for the document type, such as "ppt", "letter", "resume", "article", "section_edit", etc.
- confidence: Your confidence in this classification, a float between 0-1
- additional_info: An optional object containing other relevant information extracted from the user request"""
    
    try:
        # Use the unified LLM utility to get the response
        response_content = await generate_text(
            prompt=f"{message}\n\n{format_instructions}",
            system_message=system_prompt,
            model=model,
            temperature=temperature,
            streaming=False,
            response_format={"type": "json_object"}
        )
        
        # Parse JSON response
        try:
            data = json.loads(response_content)
            return DocumentIntent(**data)
        except json.JSONDecodeError as e:
            # Try to extract JSON from the response if direct parsing fails
            try:
                json_start = response_content.find('{')
                json_end = response_content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_content[json_start:json_end]
                    data = json.loads(json_str)
                    return DocumentIntent(**data)
                else:
                    raise ValueError("No valid JSON found in response")
            except Exception as e2:
                logger.error(f"Failed to parse JSON response: {e2}")
                return DocumentIntent(
                    document_type="unknown",
                    confidence=0.0,
                    additional_info={"error": f"JSON parsing error: {str(e2)}", "raw_response": response_content}
                )
    except Exception as e:
        logger.error(f"Error during LLM call: {str(e)}")
        return DocumentIntent(
            document_type="unknown",
            confidence=0.0,
            additional_info={"error": str(e)}
        )
