"""
Service for handling create new content requests.
"""
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from pathlib import Path
import os
from app.utils.llm_utils import generate_text

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

async def confirm_create_new_intent(message: str, model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    """
    Analyze the user's original message to confirm and describe the specific content creation intent.
    This function analyzes the user's message to provide a detailed description of what they want to create.
    
    Args:
        message: The original user message
        model: The LLM model to use
        temperature: Temperature setting for the LLM
        
    Returns:
        A string describing the specific content creation intent
    """
    system_prompt = """You are an AI assistant that analyzes user requests to create new content.
    Your task is to identify the specific type of content the user wants to create and provide
    a clear, concise description of what they want to do.
    
    Analyze the user's message and categorize it into one of these content creation types:
    1. Document/Article - Creating structured written content
    2. List/Outline - Creating organized lists or outlines
    3. Creative Writing - Stories, poems, creative content
    4. Technical Content - Code, documentation, technical writing
    5. Business Content - Reports, proposals, business documents
    6. Educational Content - Lessons, explanations, tutorials
    
    Provide a brief, friendly description (1-2 sentences) of what the user wants to create.
    Focus on being encouraging and showing understanding of their request.
    
    Example responses:
    - "I'll help you create a professional business proposal with clear structure and compelling content."
    - "Let me create an engaging story based on your creative ideas."
    - "I'll generate a comprehensive tutorial that explains the topic step by step."
    """
    
    try:
        # Use the unified generate_text function
        response = await generate_text(
            prompt=f"User request: {message}",
            system_message=system_prompt,
            model=model,
            temperature=temperature,
            streaming=False  # We want complete response for intent confirmation
        )
        
        return response.strip()
            
    except Exception as e:
        logger.error(f"Error in confirm_create_new_intent: {e}")
        return "I'll help you create the content you requested."

async def generate_new_content(
    user_message: str,
    create_new_intent: Dict[str, Any],
    model: str = "gpt-4o",
    temperature: float = 0.7
) -> str:
    """
    Generate new content based on user request and intent analysis.
    
    Args:
        user_message: The original user message
        create_new_intent: The analyzed intent data
        model: The LLM model to use
        temperature: Temperature setting for the LLM
        
    Returns:
        The generated content
    """
    try:
        
        # Extract intent information with defaults
        document_type = create_new_intent.get('document_type', 'general')
        expected_length = create_new_intent.get('expected_length', 'medium')
        tone = create_new_intent.get('tone', 'professional')
        purpose = create_new_intent.get('purpose', 'general purpose')
        target_audience = create_new_intent.get('target_audience', 'general audience')
        
        # Build length guidance
        length_guidance = {
            'short': 'Keep it concise, around 1-2 paragraphs or 100-200 words.',
            'medium': 'Provide moderate detail, around 3-5 paragraphs or 300-500 words.',
            'long': 'Provide comprehensive detail, around 6+ paragraphs or 500+ words.',
            'very_long': 'Create extensive content with multiple sections, 1000+ words.'
        }.get(expected_length, 'Provide appropriate length based on the content type.')
        
        # Build document type specific guidance
        type_guidance = {
            'letter': 'Format as a formal letter with proper greeting, body, and closing.',
            'email': 'Format as a professional email with subject, greeting, body, and signature.',
            'report': 'Structure with clear sections, headings, and professional formatting.',
            'article': 'Create engaging content with introduction, main points, and conclusion.',
            'essay': 'Structure with introduction, body paragraphs, and conclusion.',
            'story': 'Create narrative content with characters, plot, and engaging storytelling.',
            'poem': 'Use appropriate poetic structure, rhythm, and literary devices.',
            'list': 'Format as a well-organized list with clear items and descriptions.',
            'outline': 'Create hierarchical structure with main points and sub-points.',
            'proposal': 'Include problem statement, solution, benefits, and call to action.',
            'resume': 'Format professionally with sections for experience, skills, and education.',
            'cover_letter': 'Address specific job requirements and highlight relevant qualifications.'
        }.get(document_type, 'Create well-structured content appropriate for the requested type.')
        
        # Build comprehensive system prompt
        system_prompt = f"""You are a professional content creator with expertise in various document types and writing styles.

Task: Create high-quality content based on the user's specific request.

Content Specifications:
- Document Type: {document_type}
- Purpose: {purpose}
- Target Audience: {target_audience}
- Tone: {tone}
- Length: {expected_length}

Length Guidance: {length_guidance}

Type-Specific Guidance: {type_guidance}

Quality Standards:
1. Create content that directly and completely fulfills the user's request
2. Ensure the content is well-structured and professionally formatted
3. Use the specified tone consistently throughout
4. Make the content engaging, valuable, and appropriate for the target audience
5. Include relevant details and examples where appropriate
6. Ensure proper grammar, spelling, and punctuation

Output Instructions:
- Generate ONLY the content that should be inserted into the document
- Do not include any explanations, meta-commentary, or instructions
- Do not wrap the content in quotes or code blocks
- Start directly with the content itself"""
        
        # Use the unified generate_text function
        content = await generate_text(
            prompt=f"User request: {user_message}",
            system_message=system_prompt,
            model=model,
            temperature=temperature,
            streaming=False  # We want complete response for content generation
        )
        
        # Remove any unwanted wrapping that might have been added
        if content.startswith('```') and content.endswith('```'):
            # Remove code block wrapping
            lines = content.split('\n')
            if len(lines) > 2:
                content = '\n'.join(lines[1:-1])
        
        # Remove quotes if the entire content is wrapped in them
        if (content.startswith('"') and content.endswith('"')) or (content.startswith("'") and content.endswith("'")):
            content = content[1:-1]
        
        return content
            
    except Exception as e:
        logger.error(f"Error in generate_new_content: {e}")
        # Return a more helpful error message
        return f"I apologize, but I encountered an error while generating the content: {str(e)}. Please try again or rephrase your request."

async def generate_content_explanation(
    user_request: str,
    generated_content: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3
) -> str:
    """
    Generate an explanation of what content was created.
    
    Args:
        user_request: The original user request
        generated_content: The content that was generated
        model: The LLM model to use
        temperature: Temperature setting for the LLM
        
    Returns:
        A brief explanation of what was created
    """
    try:
        # Analyze content characteristics
        content_length = len(generated_content)
        word_count = len(generated_content.split())
        line_count = len(generated_content.split('\n'))
        
        # Determine content type based on structure
        content_type = "content"
        if generated_content.count('\n\n') > 2:
            content_type = "multi-section document"
        elif generated_content.startswith(('Dear ', 'To:', 'Subject:')):
            content_type = "letter or email"
        elif generated_content.count('\n-') > 2 or generated_content.count('\n*') > 2:
            content_type = "list or outline"
        elif generated_content.count('\n#') > 1:
            content_type = "structured document with headings"
        elif word_count < 50:
            content_type = "brief content"
        elif word_count > 500:
            content_type = "comprehensive content"
        

        
        system_prompt = f"""You are an AI assistant that explains what content was created for the user.
        Provide a brief, friendly explanation (1-2 sentences) of what was generated.
        Focus on the key aspects of the content and how it addresses the user's request.
        
        Content Analysis:
        - Content type: {content_type}
        - Word count: {word_count} words
        - Structure: {line_count} lines
        
        Guidelines:
        1. Be specific about what was created
        2. Mention key features or structure if relevant
        3. Keep it concise but informative
        4. Use a friendly, helpful tone
        5. Focus on how it fulfills the user's request
        
        Example responses:
        - "I've created a professional business proposal with clear sections covering your project overview, timeline, and budget requirements."
        - "I've written an engaging {word_count}-word story based on your creative prompt, featuring vivid characters and an interesting plot."
        - "I've generated a comprehensive tutorial that explains the concept step-by-step with practical examples and clear explanations."
        - "I've prepared a well-structured outline with main points and sub-sections to help organize your ideas."
        - "I've crafted a professional email that addresses your specific requirements and maintains an appropriate tone."
        """
        
        # Prepare prompt with more context
        content_preview = generated_content[:300] + "..." if len(generated_content) > 300 else generated_content
        prompt = f"User request: {user_request}\n\nGenerated content preview:\n{content_preview}"
        
        # Use the unified generate_text function
        explanation = await generate_text(
            prompt=prompt,
            system_message=system_prompt,
            model=model,
            temperature=temperature,
            streaming=False  # We want complete response for explanation
        )
        
        # Fallback to a more informative default if the response is too generic
        if explanation.lower() in ['content has been created.', 'content created.', 'done.']:
            explanation = f"I've created {content_type} with {word_count} words based on your request."
        
        return explanation
            
    except Exception as e:
        logger.error(f"Error in generate_content_explanation: {e}")
        # Provide a more informative fallback
        word_count = len(generated_content.split()) if generated_content else 0
        return f"I've successfully created content with {word_count} words based on your request."

def format_content_for_insertion(content: str) -> str:
    """
    Format content for insertion into the editor.
    
    Args:
        content: The raw content to format
        
    Returns:
        Formatted content ready for insertion
    """
    if not content:
        return ""
    
    # Remove excessive whitespace while preserving intentional formatting
    lines = content.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Strip trailing whitespace but preserve leading whitespace for indentation
        formatted_line = line.rstrip()
        formatted_lines.append(formatted_line)
    
    # Join lines and ensure proper ending
    formatted_content = '\n'.join(formatted_lines)
    
    # Remove excessive blank lines at the beginning and end
    formatted_content = formatted_content.strip()
    
    # Ensure content ends with appropriate spacing for editor
    if formatted_content and not formatted_content.endswith('\n'):
        formatted_content += '\n'
    
    return formatted_content

def analyze_content_structure(content: str) -> Dict[str, Any]:
    """
    Analyze the structure of generated content.
    
    Args:
        content: The content to analyze
        
    Returns:
        Dictionary with content analysis results
    """
    if not content:
        return {
            'word_count': 0,
            'line_count': 0,
            'paragraph_count': 0,
            'content_type': 'empty',
            'has_headings': False,
            'has_lists': False,
            'estimated_reading_time': 0
        }
    
    lines = content.split('\n')
    words = content.split()
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    # Detect content features
    has_headings = any(line.strip().startswith('#') for line in lines)
    has_lists = any(line.strip().startswith(('-', '*', '+')) or 
                   any(line.strip().startswith(f'{i}.') for i in range(1, 10)) 
                   for line in lines)
    
    # Estimate reading time (average 200 words per minute)
    estimated_reading_time = max(1, len(words) // 200)
    
    # Determine content type
    content_type = 'text'
    if has_headings:
        content_type = 'structured_document'
    elif has_lists:
        content_type = 'list_or_outline'
    elif len(paragraphs) > 3:
        content_type = 'multi_paragraph_text'
    elif content.startswith(('Dear ', 'To:', 'Subject:')):
        content_type = 'correspondence'
    
    return {
        'word_count': len(words),
        'line_count': len(lines),
        'paragraph_count': len(paragraphs),
        'content_type': content_type,
        'has_headings': has_headings,
        'has_lists': has_lists,
        'estimated_reading_time': estimated_reading_time
    }
