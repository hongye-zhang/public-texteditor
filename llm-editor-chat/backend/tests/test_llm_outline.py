import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from app.features.llm.services.article_outline import ArticleOutlineRequest, generate_article_outline

async def test_article_outline():
    """Test the article outline generation functionality"""
    
    # Test case 1: Basic article outline
    request = ArticleOutlineRequest(
        article_type="Technical Blog Post",
        basic_requirements="""
        - Should be beginner-friendly
        - Include code examples
        - Cover best practices
        """,
        reference_materials=["sample1.txt", "sample2.pdf"]
    )
    
    response = await generate_article_outline(request)
    print("\nTest Case 1: Basic Article Outline")
    print("Status:", response.status)
    print("Message:", response.message)
    print("\nGenerated Outline:")
    print(response.outline)
    
    # Test case 2: Error handling (empty requirements)
    try:
        request = ArticleOutlineRequest(
            article_type="",
            basic_requirements="",
            reference_materials=[]
        )
        response = await generate_article_outline(request)
        print("\nTest Case 2: Empty Requirements")
        print("Status:", response.status)
        print("Message:", response.message)
    except Exception as e:
        print("\nTest Case 2: Error handling worked as expected")
        print("Error:", str(e))

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_article_outline())
