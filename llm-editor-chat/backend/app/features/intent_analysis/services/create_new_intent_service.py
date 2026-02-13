from typing import Optional, Dict, Any, Literal, Union
import json
import logging
from pydantic import BaseModel, Field
from pathlib import Path
from app.utils.llm_utils import generate_text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CreateNewIntent(BaseModel):
    """
    Second-level intent for create_new requests, capturing document properties and file usage intent.
    
    Attributes:
        document_type: Type of document as MIME type or standardized name
        complexity: Estimated complexity level of the document
        expected_length: Length category based on token count and chapter count (short, medium, long, very_long)
        confidence: Confidence score of the intent analysis
        file_usage_intent: How the uploaded file should be used in content creation
        additional_info: Extra details as structured data
    """
    document_type: str = Field(
        ..., 
        description="Type of document as MIME type or standardized name (e.g., application/vnd.ms-powerpoint, resume, cover_letter)"
    )
    complexity: Literal["simple", "professional"] = Field(
        ..., 
        description="Estimated complexity based on pages/slides or detail"
    )
    expected_length: str = Field(
        ..., 
        description="Length category: short (<250 tokens), medium (250-2000 tokens, <5 chapters), long (2000-8000 tokens, <10 chapters), very_long (>8000 tokens or >10 chapters)"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence score of this analysis"
    )
    file_usage_intent: Optional[Literal["content_based", "reference_only"]] = Field(
        default=None, 
        description="How the uploaded file should be used: 'content_based' means create content primarily based on the file's content; 'reference_only' means the user has their own topic and the file is just for reference"
    )
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Extra details as structured data, including specific_format, key_elements, and user_keywords"
    )

async def identify_create_new_intent(message: str, file_path: Optional[str] = None, model: str = "gpt-4.1", temperature: float = 0.0) -> CreateNewIntent:
    """
    Analyze create_new message to extract document type, complexity, word count, and file usage intent.
    
    This function uses an LLM to analyze the user's message and determine their intent
    for creating a new document. If a file path is provided, it also determines how the
    user intends to use that file (as primary content or just as a reference).
    
    Args:
        message: The user's message requesting content creation
        file_path: Optional path to a file uploaded by the user, which may influence the intent
        model: The LLM model to use for intent identification
        temperature: Temperature setting for the LLM
        
    Returns:
        CreateNewIntent object with the identified document properties and file usage intent
        
    Raises:
        ValueError: If the API response cannot be parsed as valid JSON
        Exception: For other errors during intent identification
    """
    logger.info(f"Identifying create_new intent for message: {message[:50]}...")
    if file_path:
        logger.info(f"File provided: {Path(file_path).name}")
    # 根据是否有文件路径选择不同的系统提示词
    if file_path:
        system_prompt = """
        You are a document intent analyzer that extracts structured information from user requests.
        Your task is to identify the type of document the user wants to create, its complexity, estimated word count, and how any uploaded files should be used.
        
        For document_type, use standard MIME document types or common document formats when possible, but ONLY when the user EXPLICITLY mentions the specific format:
        - application/vnd.ms-powerpoint or application/vnd.openxmlformats-officedocument.presentationml.presentation - ONLY when the user explicitly mentions "presentation", "slides", "PPT", "PowerPoint", "演示文稿", "幻灯片" or similar terms
        - application/msword or application/vnd.openxmlformats-officedocument.wordprocessingml.document - ONLY when the user explicitly mentions "Word document", "doc", "docx", "Word文档" or similar terms
        - application/pdf - ONLY when the user explicitly mentions "PDF", "portable document format" or similar terms
        - text/html - ONLY when the user explicitly mentions "HTML", "web page", "webpage", "网页" or similar terms
        - text/markdown - ONLY when the user explicitly mentions "markdown", "md", "markdown文档" or similar terms
        - text/plain - ONLY when the user explicitly mentions "plain text", "text file", "txt", "文本文件" or similar terms
        
        For common document types without direct MIME equivalents, use these standardized names, but ONLY when the user EXPLICITLY mentions the specific format:
        - resume - ONLY when the user explicitly mentions "resume", "CV", "curriculum vitae", "简历" or similar terms
        - cover_letter - ONLY when the user explicitly mentions "cover letter", "求职信", "申请信" or similar terms
        - business_plan - ONLY when the user explicitly mentions "business plan", "商业计划" or similar terms
        - research_paper - ONLY when the user explicitly mentions "research paper", "academic paper", "论文", "研究论文" or similar terms
        - technical_report - ONLY when the user explicitly mentions "technical report", "technical documentation", "技术报告" or similar terms
        - blog_post - ONLY when the user explicitly mentions "blog", "blog post", "article", "博客", "文章" or similar terms
        - email - ONLY when the user explicitly mentions "email", "e-mail", "电子邮件" or similar terms
        - contract - ONLY when the user explicitly mentions "contract", "agreement", "合同", "协议" or similar terms
        - proposal - ONLY when the user explicitly mentions "proposal", "提案", "建议书" or similar terms
        - educational_content - Use this for explanations, tutorials, lessons, study materials, or any educational content that is not explicitly specified as another format
        
        IMPORTANT: For requests to explain concepts, create tutorials, or generate educational content without specifying a particular format, use "educational_content" as the document_type.
        
        Examples:
        - "Write a PowerPoint presentation about climate change" → application/vnd.ms-powerpoint
        - "Create a Word document about business strategies" → application/msword
        - "Explain the Pythagorean theorem for 8th grade students" → educational_content
        - "Create a tutorial on Python programming" → educational_content
        - "Write an article about AI" → blog_post
        
        When a user has uploaded a file, determine their intent for using that file:
        - "content_based": The user wants to create new content primarily based on the file's content (e.g., "Create a summary of this document", "Make a presentation based on this research paper")
        - "reference_only": The user has their own topic and the file is just for reference or inspiration (e.g., "Write a report about climate change using this data as reference", "Create a resume in the style of this template")
        
        ALWAYS respond with a valid JSON object containing these fields:
        {
          "document_type": "[MIME type or standardized name]",
          "complexity": "[simple or professional]",
          "expected_length": "[short|medium|long|very_long - based on token count and chapters: short=<250 tokens, medium=250-2000 tokens & <=8 chapters, long=2000-8000 tokens & <=20 chapters, very_long=>8000 tokens or >20 chapters]",
          "confidence": [float between 0.0-1.0],
          "file_usage_intent": "[content_based or reference_only]",
          "additional_info": {
            "specific_format": "[optional format details]",
            "key_elements": ["optional array of requested elements"],
            "user_keywords": ["optional array of important keywords"],
            "purpose": "[concise description of document purpose, ≤40 chars]",
            "target_audience": ["array of target audiences, each ≤20 chars"],
            "top_concerns": ["array of audience concerns/pain points by priority, each ≤30 chars"],
            "tone": "[Formal|Professional|Conversational|Friendly|Playful]",
            "cta": "[call to action if applicable, ≤40 chars]",
            "topic_complexity": "[Low|Medium|High]",
            "missing_info": ["array of information gaps that need clarification, each ≤30 chars"]
          }
        }
        """
    else:
        # 没有文件时使用简化版的提示词，不包含文件使用意图相关内容
        system_prompt = """
        You are a document intent analyzer that extracts structured information from user requests.
        Your task is to identify the type of document the user wants to create, its complexity, and estimated word count.
        
        For document_type, use standard MIME document types or common document formats when possible, but ONLY when the user EXPLICITLY mentions the specific format:
        - application/vnd.ms-powerpoint or application/vnd.openxmlformats-officedocument.presentationml.presentation - ONLY when the user explicitly mentions "presentation", "slides", "PPT", "PowerPoint", "演示文稿", "幻灯片" or similar terms
        - application/msword or application/vnd.openxmlformats-officedocument.wordprocessingml.document - ONLY when the user explicitly mentions "Word document", "doc", "docx", "Word文档" or similar terms
        - application/pdf - ONLY when the user explicitly mentions "PDF", "portable document format" or similar terms
        - text/html - ONLY when the user explicitly mentions "HTML", "web page", "webpage", "网页" or similar terms
        - text/markdown - ONLY when the user explicitly mentions "markdown", "md", "markdown文档" or similar terms
        - text/plain - ONLY when the user explicitly mentions "plain text", "text file", "txt", "文本文件" or similar terms
        
        For common document types without direct MIME equivalents, use these standardized names, but ONLY when the user EXPLICITLY mentions the specific format:
        - resume - ONLY when the user explicitly mentions "resume", "CV", "curriculum vitae", "简历" or similar terms
        - cover_letter - ONLY when the user explicitly mentions "cover letter", "求职信", "申请信" or similar terms
        - business_plan - ONLY when the user explicitly mentions "business plan", "商业计划" or similar terms
        - research_paper - ONLY when the user explicitly mentions "research paper", "academic paper", "论文", "研究论文" or similar terms
        - technical_report - ONLY when the user explicitly mentions "technical report", "technical documentation", "技术报告" or similar terms
        - blog_post - ONLY when the user explicitly mentions "blog", "blog post", "article", "博客", "文章" or similar terms
        - email - ONLY when the user explicitly mentions "email", "e-mail", "电子邮件" or similar terms
        - contract - ONLY when the user explicitly mentions "contract", "agreement", "合同", "协议" or similar terms
        - proposal - ONLY when the user explicitly mentions "proposal", "提案", "建议书" or similar terms
        - educational_content - Use this for explanations, tutorials, lessons, study materials, or any educational content that is not explicitly specified as another format
        
        IMPORTANT: For requests to explain concepts, create tutorials, or generate educational content without specifying a particular format, use "educational_content" as the document_type.
        
        Examples:
        - "Write a PowerPoint presentation about climate change" → application/vnd.ms-powerpoint
        - "Create a Word document about business strategies" → application/msword
        - "Explain the Pythagorean theorem for 8th grade students" → educational_content
        - "Create a tutorial on Python programming" → educational_content
        - "Write an article about AI" → blog_post
        
        ALWAYS respond with a valid JSON object containing these fields:
        {
          "document_type": "[MIME type or standardized name]",
          "complexity": "[simple or professional]",
          "expected_length": "[short|medium|long|very_long - based on token count and chapters: short=<250 tokens, medium=250-2000 tokens & <=8 chapters, long=2000-8000 tokens & <=20 chapters, very_long=>8000 tokens or >20 chapters]",
          "confidence": [float between 0.0-1.0],
          "additional_info": {
            "specific_format": "[optional format details]",
            "key_elements": ["optional array of requested elements"],
            "user_keywords": ["optional array of important keywords"],
            "purpose": "[concise description of document purpose, ≤40 chars]",
            "target_audience": ["array of target audiences, each ≤20 chars"],
            "top_concerns": ["array of audience concerns/pain points by priority, each ≤30 chars"],
            "tone": "[Formal|Professional|Conversational|Friendly|Playful]",
            "cta": "[call to action if applicable, ≤40 chars]",
            "topic_complexity": "[Low|Medium|High]",
            "missing_info": ["array of information gaps that need clarification, each ≤30 chars"]
          }
        }
        """
    
    # Include file information in the prompt if available
    file_info = ""
    if file_path:
        file_name = Path(file_path).name
        file_ext = Path(file_path).suffix.lower()
        file_info = f"\n\nThe user has uploaded a file: {file_name} (extension: {file_ext}). " 
        file_info += "Analyze whether the user wants to create content primarily based on this file's content ('content_based') "
        file_info += "or if they have their own topic and the file is just for reference ('reference_only'). "
        file_info += "This is crucial for determining how to process the request."
    
    user_prompt = f"Based on this request, identify the document intent: {message}{file_info}"
    
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
        
        # Try to parse the JSON response
        try:
            intent_data = json.loads(response_content)
            return CreateNewIntent(**intent_data)
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract JSON from the response
            try:
                # Try to find JSON in the response using string manipulation
                json_start = response_content.find('{')
                json_end = response_content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_content[json_start:json_end]
                    intent_data = json.loads(json_str)
                    return CreateNewIntent(**intent_data)
                else:
                    # If no JSON found, return a default intent with low confidence
                    return CreateNewIntent(
                        document_type="text/plain",
                        complexity="simple",
                        word_count=100,
                        confidence=0.1,
                        additional_info={"error": "Failed to parse LLM response as JSON"}
                    )
            except Exception as e2:
                # If all parsing attempts fail, return a default intent with low confidence
                return CreateNewIntent(
                    document_type="text/plain",
                    complexity="simple",
                    word_count=100,
                    confidence=0.1,
                    additional_info={"error": f"Failed to parse LLM response: {str(e2)}"}
                )
            # If all parsing attempts fail, return a default intent with low confidence
            return CreateNewIntent(
                document_type="text/plain",
                complexity="simple",
                word_count=100,
                confidence=0.1,
                additional_info={"error": f"Failed to parse LLM response: {str(e2)}"}
            )
    
    except Exception as e:
        logger.error(f"Error during LLM call: {str(e)}")
        # Provide fallback values if we couldn't complete the LLM call
        fallback_data = {
            "document_type": "text/plain",
            "complexity": "simple",
            "word_count": 100,
            "confidence": 0.1,
            "additional_info": {"error": f"LLM call failed: {str(e)}"}
        }
        if file_path:
            fallback_data["file_usage_intent"] = "reference_only"
            fallback_data["additional_info"]["has_file"] = True
            fallback_data["additional_info"]["file_path"] = file_path
        
        logger.info("Using fallback intent values due to LLM call failure")
        return CreateNewIntent(**fallback_data)
