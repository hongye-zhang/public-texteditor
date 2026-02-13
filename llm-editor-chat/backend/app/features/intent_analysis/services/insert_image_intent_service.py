from typing import Optional, Literal, Dict, Any
import json
import re
from pydantic import BaseModel, Field
from app.utils.llm_utils import generate_text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InsertImageIntent(BaseModel):
    """Second-level intent for insert_image: aesthetic vs conceptual"""
    image_type: Literal["aesthetic", "conceptual"] = Field(
        description="Type of image requested: aesthetic for photos/art, conceptual for diagrams"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of this analysis")
    additional_info: Optional[Dict[str, Any]] = Field(default=None, description="Extra details for image intent")

async def identify_insert_image_intent(message: str, model: str = "gpt-4o", temperature: float = 0.0) -> InsertImageIntent:
    """
    Analyze insert_image message to classify image type and details
    """
    prompt = (
        "You are an AI assistant specialized in extracting image insertion intents.\n\n"
        f"### User Message\n\"\"\"\n{message}\n\"\"\"\n\n"
        "### Task\n"
        "Analyze the message and classify whether the user wants an aesthetic image (photo, artwork, illustration) "
        "or a conceptual image (diagram, chart, flowchart, mind map).\n\n"
        "### Output Format\n"
        "Return ONLY a valid JSON object with the following schema:\n"
        "```json\n"
        "{\n"
        '  "image_type": string,  // MUST be exactly "aesthetic" or "conceptual"\n'
        '  "confidence": number,  // MUST be between 0.0 and 1.0\n'
        '  "additional_info": {   // Optional structured information about the request\n'
        '    "style": string,     // Optional style description\n'
        '    "subject": string,   // Optional main subject\n'
        '    "format": string     // Optional format preference\n'
        '  }\n'
        "}\n"
        "```\n\n"
        "### Examples\n"
        "For: \"Create a beautiful sunset over mountains\"\n"
        "```json\n"
        "{\n"
        '  "image_type": "aesthetic",\n'
        '  "confidence": 0.95,\n'
        '  "additional_info": {\n'
        '    "style": "photography",\n'
        '    "subject": "sunset over mountains"\n'
        '  }\n'
        "}\n"
        "```\n\n"
        "For: \"Make a flowchart showing how HTTP requests work\"\n"
        "```json\n"
        "{\n"
        '  "image_type": "conceptual",\n'
        '  "confidence": 0.98,\n'
        '  "additional_info": {\n'
        '    "style": "flowchart",\n'
        '    "subject": "HTTP requests"\n'
        '  }\n'
        "}\n"
        "```\n\n"
        "IMPORTANT: Respond with ONLY the JSON object. No explanations, no markdown formatting, no additional text."
    )
    try:
        # Use the unified LLM utility to get the response
        response_content = await generate_text(
            prompt=message,
            system_message=prompt,
            model=model,
            temperature=temperature,
            streaming=False,
            response_format={"type": "json_object"}
        )
        
        # Try to parse the JSON response
        try:
            data = json.loads(response_content)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON using regex
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    return InsertImageIntent(image_type="aesthetic", confidence=0.1)
            else:
                logger.error(f"No JSON structure found in response: {response_content}")
                return InsertImageIntent(image_type="aesthetic", confidence=0.1)
        
        # Validate required fields
        if "image_type" not in data or "confidence" not in data:
            logger.warning(f"Missing required fields in JSON: {data}")
            data.setdefault("image_type", "aesthetic")
            data.setdefault("confidence", 0.1)
            
    except Exception as e:
        logger.error(f"Error during LLM call: {str(e)}")
        return InsertImageIntent(image_type="aesthetic", confidence=0.1, additional_info={"error": str(e)})
    
    return InsertImageIntent(**data)
