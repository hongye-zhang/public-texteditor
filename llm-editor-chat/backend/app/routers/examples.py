from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/examples", tags=["examples"])

class HelloWorldResponse(BaseModel):
    """Hello World example response model"""
    content: str
    type: str = "markdown"
    version: str = "1.0"

@router.post("/helloworld")
async def hello_world() -> HelloWorldResponse:
    """Returns a Hello World example text for testing editor functionality.
    
    Returns:
        HelloWorldResponse: Response object containing the example text content
    """
    return HelloWorldResponse(
        content="""# Hello World Example

This is a basic example text for testing the editor's insert functionality.

## Features included:
- Markdown formatting
- Multi-level headings
- List items

Enjoy using the editor!"""
    )
