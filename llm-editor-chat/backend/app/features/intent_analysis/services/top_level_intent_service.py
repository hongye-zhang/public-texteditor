from typing import Optional, Dict, Any, Literal
import json
from pydantic import BaseModel, Field
from app.utils.llm_utils import generate_text

class TopLevelIntent(BaseModel):
    """Model for top-level user intent"""
    intent_type: Literal["create_new", "modify_existing", "question_only", "insert_image", "read_file", "other"] = Field(
        description="Top-level intent type: create_new (write new content), modify_existing (edit existing content), question_only (just asking/discussing), insert_image, read_file (read and operate), other"
    )
    confidence: float = Field(
        description="Confidence score of intent recognition, a float between 0-1",
        ge=0.0,
        le=1.0
    )
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional intent-related information to help with sub-intent classification"
    )

async def identify_top_level_intent(message: str, model: str = "gpt-4.1", temperature: float = 0.0) -> TopLevelIntent:
    """
    Identify the top-level intent from user messages
    
    Args:
        message: Original user input text
        model: Language model name to use
        temperature: Temperature parameter for model generation diversity
        
    Returns:
        TopLevelIntent: Identified top-level user intent
    """
    # 直接使用提示和手动JSON解析，不需要专门的parser
    
    # System prompt - Cross-intent detection approach
    system_prompt = """You are an advanced intent recognition assistant with cross-intent detection capabilities. Your task is to analyze user requests across multiple dimensions:

1. PRIMARY TASK - INTENT CLASSIFICATION: Classify the user's request into ONE of these categories:

   a. create_new - When the user wants to write or generate ENTIRELY new content or append content at the very end of a document. This includes:
      - Writing completely new documents (e.g., "write a letter", "create a presentation", "draft an email")
      - Creating educational content as a new document (e.g., "explain quantum physics", "write a tutorial on Python", "create a lesson plan")
      - Generating text that is meant to be inserted at the end of the document or as a standalone document
      - NOTE: This should NOT include inserting content in the middle of existing text or between paragraphs

   b. modify_existing - When the user wants to edit, change, or improve existing content. This includes:
      - Editing or improving existing text (e.g., "fix this paragraph", "improve the introduction", "rewrite this section")
      - Inserting content in the middle of existing text or between paragraphs (e.g., "insert a paragraph before section 2", "add a sentence between these two paragraphs")
      - Deleting content (e.g., "remove the third paragraph", "delete this sentence", "clear the introduction")
      - Reordering content (e.g., "move this paragraph to the beginning", "swap these two sections", "change the order of the bullet points")
      - Formatting changes (e.g., "make this text bold", "convert this to a bulleted list", "add headings to each section")
      - Splitting or merging content (e.g., "split this paragraph into two", "combine these sentences")
      - Replacing specific words or phrases (e.g., "replace all instances of 'client' with 'customer'")
      - Any operation that modifies the structure, organization, or formatting of existing content

   c. question_only - When the user is ONLY asking a question or discussing something, with NO intention to create content for the editor. This should ONLY be used when:
      - The user explicitly states they don't want to modify content (e.g., "just answer this question, don't edit anything")
      - The user is clearly asking for information for their own understanding, not to create content (e.g., "what's the difference between X and Y?")
      - The question is simple, factual, and doesn't require generating educational content

   d. insert_image - When the user wants to insert or generate an image (e.g., "add a picture of mountains", "insert a diagram", "create a flowchart")

   e. read_file - When the user wants to read a file and then operate on it (e.g., "read my resume and help me improve it", "open the file and summarize it")

   f. other - Any other intent that doesn't fit into the above categories

   IMPORTANT: Requests for explanations, tutorials, lessons, or educational content should be classified as "create_new" NOT "question_only", as they typically result in content that would be inserted into the editor.

2. SECONDARY TASK - CONVERSATION HISTORY RELEVANCE: Determine if the current user message is related to previous conversation history. Classify into one of:
   - "continuation": The message directly continues or builds upon previous conversation
   - "reference": The message references previous conversation but introduces a new topic
   - "independent": The message appears to be completely independent of previous conversation

3. TERTIARY TASK - LANGUAGE DETECTION: Identify the primary language used in the user's message, such as "english", "chinese", "spanish", etc.

Based on the user's message, determine all three dimensions and provide your confidence level for the primary intent classification (a number between 0-1).

Your answer must be a valid JSON object containing the following fields:
- intent_type: String identifier for the primary intent type, must be one of: "create_new", "modify_existing", "question_only", "insert_image", "read_file", "other"
- confidence: Your confidence in this primary intent classification, a float between 0-1
- additional_info: An object containing other relevant information:
  - likely_document_type/content_type: If applicable, what type of document or content is being requested
  - conversation_history_relevance: One of "continuation", "reference", "independent"
  - language: The detected primary language of the user's message
  - welcome_message: A friendly acknowledgment message in the same language as the user's input, showing the system understands their request
  - Any other context-specific details that might help with sub-intent classification

For example, if the user says "Write me a cover letter for a software engineering job", you should return:
```json
{
  "intent_type": "create_new",
  "confidence": 0.95,
  "additional_info": {
    "likely_document_type": "letter",
    "purpose": "job application",
    "role": "software engineering",
    "conversation_history_relevance": "independent",
    "language": "english",
    "welcome_message": "I'll help you create a professional cover letter for your software engineering job application!"
  }
}
```

If the user says "Explain the Pythagorean theorem for 8th grade students" in a fresh conversation, you should return:
```json
{
  "intent_type": "create_new",
  "confidence": 0.9,
  "additional_info": {
    "content_type": "educational",
    "subject": "mathematics",
    "audience": "8th grade students",
    "conversation_history_relevance": "independent",
    "language": "english",
    "welcome_message": "I'll create an engaging explanation of the Pythagorean theorem that's perfect for 8th grade students!"
  }
}
```

If the user says "What's the capital of France? Just answer the question please.", you should return:
```json
{
  "intent_type": "question_only",
  "confidence": 0.95,
  "additional_info": {
    "question_type": "factual",
    "explicit_instruction": "just answer",
    "conversation_history_relevance": "independent",
    "language": "english",
    "welcome_message": "Got it! The capital of France is Paris."
  }
}
```

If the user says "Can you fix the grammar in this paragraph?" after previously discussing a draft, you should return:
```json
{
  "intent_type": "modify_existing",
  "confidence": 0.90,
  "additional_info": {
    "modification_type": "grammar_correction",
    "scope": "paragraph",
    "conversation_history_relevance": "continuation",
    "language": "english",
    "welcome_message": "I'll help you fix the grammar in that paragraph!"
  }
}
```

If the user says "帮我写一份简历" (Help me write a resume), you should return:
```json
{
  "intent_type": "create_new",
  "confidence": 0.95,
  "additional_info": {
    "likely_document_type": "resume",
    "conversation_history_relevance": "independent",
    "language": "chinese",
    "welcome_message": "好的！我来帮您创建一份专业的简历。"
  }
}
```"""
    
    # Create format instructions
    format_instructions = """You must return a valid JSON object containing the following fields:
- intent_type: String identifier for the intent type, must be one of: "create_new", "modify_existing", "question_only", "insert_image", "other"
- confidence: Your confidence in this classification, a float between 0-1
- additional_info: An optional object containing other relevant information extracted from the user request"""
    
    # Create user prompt
    user_prompt = f"{message}\n\n{format_instructions}"
    
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
            intent_data = json.loads(response_content)
            return TopLevelIntent(**intent_data)
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract JSON from the response
            try:
                # Try to find JSON in the response using string manipulation
                json_start = response_content.find('{')
                json_end = response_content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_content[json_start:json_end]
                    intent_data = json.loads(json_str)
                    return TopLevelIntent(**intent_data)
                else:
                    # If no JSON found, return a default intent with low confidence
                    return TopLevelIntent(
                        intent_type="other",
                        confidence=0.1,
                        additional_info={"error": "Failed to parse LLM response as JSON"}
                    )
            except Exception as e2:
                # If all parsing attempts fail, return a default intent with low confidence
                return TopLevelIntent(
                    intent_type="other",
                    confidence=0.1,
                    additional_info={"error": f"Failed to parse LLM response: {str(e2)}"}
                )
    except Exception as e:
        # If the unified LLM utility call fails, return a default intent with low confidence
        return TopLevelIntent(
            intent_type="other",
            confidence=0.1,
            additional_info={"error": f"Failed to call LLM utility: {str(e)}"}
        )
