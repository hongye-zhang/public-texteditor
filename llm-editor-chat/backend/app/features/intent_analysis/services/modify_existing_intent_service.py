from typing import Optional, Dict, Any, Literal, Union
import json
from pydantic import BaseModel, Field
from app.utils.llm_utils import generate_text

class ModifyExistingIntent(BaseModel):
    """Second-level intent for modify_existing: action (insert/replace/delete) and content."""
    action: Literal['insert','replace','delete'] = Field(..., description="Modification action to perform")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of this action intent")
    additional_info: Optional[Union[Dict[str, Any], str]] = Field(default=None, description="Extra details for action intent")
    
    @property
    def content(self) -> Optional[str]:
        """Extract content from additional_info if available"""
        if isinstance(self.additional_info, dict) and 'content' in self.additional_info:
            return self.additional_info['content']
        elif isinstance(self.additional_info, str):
            return self.additional_info
        return None
        
    @property
    def search_query(self) -> Optional[str]:
        """Extract search_query from additional_info if available"""
        if isinstance(self.additional_info, dict) and 'search_query' in self.additional_info:
            return self.additional_info['search_query']
        return None
        
    @property
    def location(self) -> Optional[str]:
        """Extract location from additional_info if available"""
        if isinstance(self.additional_info, dict) and 'location' in self.additional_info:
            return self.additional_info['location']
        return None
        
    @property
    def section(self) -> Optional[str]:
        """Extract section from additional_info if available"""
        if isinstance(self.additional_info, dict) and 'section' in self.additional_info:
            return self.additional_info['section']
        return None

async def identify_modify_existing_intent(message: str, model: str = "gpt-4o", temperature: float = 0.0) -> ModifyExistingIntent:
    """
    Analyze modify_existing message to extract modification scope and details
    """
    system_prompt = """You are an AI assistant that analyzes user requests to modify existing content. 
    Extract the modification intent and return it in a structured JSON format.
    
    The JSON should have these fields:
    - action: The type of modification (insert/replace/delete)
    - confidence: Your confidence in this classification (0-1)
    - additional_info: Any additional details about the modification
    """
    
    user_prompt = f"User wants to modify content: {message}"
    
    try:
        # Get the response from the model using the unified LLM utility
        response_content = await generate_text(
            prompt=user_prompt,
            system_message=system_prompt,
            model=model,
            temperature=temperature,
            streaming=False,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        try:
            data = json.loads(response_content.strip())
        except json.JSONDecodeError:
            # fallback parse code block
            if "```json" in response_content:
                block = response_content.split("```json")[1].split("```")[0]
                data = json.loads(block.strip())
            else:
                # Try to extract JSON from the response
                json_start = response_content.find('{')
                json_end = response_content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_content[json_start:json_end]
                    data = json.loads(json_str)
                else:
                    data = {}
        
        # Only pass recognized keys to model
        return ModifyExistingIntent(**{k: data.get(k) for k in ['action', 'confidence', 'additional_info'] if k in data})
        
    except Exception as e:
        # If any error occurs, return a default intent with low confidence
        return ModifyExistingIntent(
            action='replace',  # Default to replace as it's the safest option
            confidence=0.1,
            additional_info={"error": f"Failed to process intent: {str(e)}"}
        )

async def confirm_modify_intent(message: str, model: str = "gpt-4.1-mini", temperature: float = 0.7) -> str:
    """
    Analyze the user's original message to confirm and describe the specific modification intent.
    This function doesn't rely on the intent data from top-level intent recognition but directly
    analyzes the user's message to provide a more detailed description of the modification intent.
    
    Args:
        message: The original user message
        model: The LLM model to use
        temperature: Temperature setting for the LLM
        
    Returns:
        A string describing the specific modification intent
    """
    system_prompt = """You are an AI assistant that analyzes user requests to modify existing content.
    Your task is to identify the specific type of modification the user is requesting and provide
    a clear, concise description of what they want to do.
    
    Analyze the user's message and categorize it into one of these modification types:
    1. Editing/Improving - Changes that enhance quality without changing structure
    2. Inserting - Adding new content at specific locations
    3. Deleting - Removing specific content
    4. Reordering - Changing the sequence or organization of content
    5. Formatting - Changing appearance or structure without altering content
    6. Splitting/Merging - Dividing content or combining separate elements
    7. Replacing - Substituting specific words, phrases or sections
    8. Other structural modifications - Any other changes to structure or organization
    
    Your response should have two parts:
    1. First, if the user is making a specific request, acknowledge that you understand their request clearly.
       If the user is suggesting an idea or making a recommendation, start by praising their idea.
    2. Then, provide a brief description (1-2 sentences) that clearly explains:
       - The specific modification type
       - What content is being modified
       - How it's being modified
    
    DO NOT include any explanations, justifications, or additional commentary beyond these two parts.
    DO NOT use phrases like "The user wants to" or "This is a request to".
    """
    
    # 读取top_intent，然后读取language设置，并把语言设置添加到system_prompt之后
    from app.features.chat.router import get_current_intent
    
    # 获取当前的top_level_intent
    top_intent = get_current_intent()
    
    # 默认使用中文，如果top_intent存在且有language属性，则使用该属性
    language = "English"
    if top_intent and hasattr(top_intent, 'additional_info') and top_intent.additional_info:
        if isinstance(top_intent.additional_info, dict) and 'language' in top_intent.additional_info:
            language = top_intent.additional_info['language']
    
    # 将语言设置添加到system_prompt
    system_prompt += f"""
    
    Output in {language}. 
    """
    
    user_prompt = message
    
    try:
        # Get the response from the model using the unified LLM utility
        response_content = await generate_text(
            prompt=user_prompt,
            system_message=system_prompt,
            model=model,
            temperature=temperature,
            streaming=False
        )
        
        # Return the raw response as the intent description
        return response_content.strip()
        
    except Exception as e:
        # If any error occurs, return a generic description
        return f"Modify existing content based on user request. (Error: {str(e)})"