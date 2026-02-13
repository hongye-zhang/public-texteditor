"""Article outline generation service.

This module provides functionality for generating article outlines using LLM.
"""
from typing import List, Optional
from pydantic import BaseModel

class ArticleOutlineRequest(BaseModel):
    """Request model for article outline generation"""
    article_type: str
    basic_requirements: str
    reference_materials: Optional[List[str]] = None  # List of file paths

class ArticleOutlineResponse(BaseModel):
    """Response model for article outline generation"""
    outline: str
    status: str = "success"
    message: str = "Outline generated successfully"

def build_outline_prompt(article_type: str, basic_requirements: str, reference_materials: List[str]) -> str:
    """Build the complete prompt for article outline generation"""
    return f"""You are tasked with creating an outline for an article based on specific requirements and reference materials. Your goal is to produce a well-structured outline that adheres to the given guidelines and incorporates relevant information from the provided resources.

First, review the type of article you will be outlining:
<article_type>
{article_type}
</article_type>

Next, carefully read and understand the basic requirements for writing the article:
<basic_requirements>
{basic_requirements}
</basic_requirements>

Now, examine the reference materials provided:
<reference_materials>
{', '.join(reference_materials) if reference_materials else 'No reference materials provided'}
</reference_materials>

To create an effective outline, follow these steps:

1. Analyze the basic requirements:
   - Carefully review the structure and key points mentioned in the basic requirements.
   - Make note of any specific writing methods or approaches suggested.
   - Ensure that your outline will align closely with these requirements.

2. Read and analyze the reference materials:
   - Thoroughly read all provided reference materials.
   - Identify and list the main points and key information from each source.
   - Consider how these points relate to the article type and basic requirements.

3. Create the outline:
   - Develop a title for the article that reflects its content and purpose.
   - Structure the outline with main chapters or sections.
   - For each chapter or section:
     a. Create a clear and concise heading.
     b. Briefly describe which points from the reference materials you plan to use.
     c. Indicate how these points relate to the basic requirements.

4. Review and refine:
   - Ensure that your outline covers all necessary aspects mentioned in the basic requirements.
   - Check that you've incorporated relevant information from all reference materials.
   - Verify that the structure is logical and flows well.

Present your outline in the following format:
<outline>
Title: [Your proposed title for the article]

1. [Chapter/Section 1 Title]
   - Key points to cover: [Brief description]
   - Reference material(s) to use: [Specify which reference(s) and what information]

2. [Chapter/Section 2 Title]
   - Key points to cover: [Brief description]
   - Reference material(s) to use: [Specify which reference(s) and what information]

[Continue with additional chapters/sections as needed]
</outline>"""

async def generate_article_outline(request: ArticleOutlineRequest) -> ArticleOutlineResponse:
    """Generate an article outline based on the given parameters and reference materials.
    
    Args:
        request (ArticleOutlineRequest): The request containing article type, requirements and references
        
    Returns:
        ArticleOutlineResponse: The generated outline
    """
    try:
        # Build the complete prompt
        prompt = build_outline_prompt(
            request.article_type,
            request.basic_requirements,
            request.reference_materials or []
        )
        
        # Here we'll add the actual LLM integration later
        # For now, return a mock response
        mock_outline = f"""Title: Sample Article on {request.article_type}

1. Introduction
   - Key points to cover: Overview of the topic
   - Reference material(s) to use: None

2. Main Content
   - Key points to cover: Core concepts and analysis
   - Reference material(s) to use: All provided references

3. Conclusion
   - Key points to cover: Summary and key takeaways
   - Reference material(s) to use: None"""

        return ArticleOutlineResponse(outline=mock_outline)
        
    except Exception as e:
        return ArticleOutlineResponse(
            outline="",
            status="error",
            message=f"Failed to generate outline: {str(e)}"
        )
