"""
Test script for the LLM service.

This script demonstrates how to use the LLM service to generate responses.
"""
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@asynccontextmanager
async def get_llm_service():
    """Context manager to handle LLM service lifecycle."""
    from app.features.llm.services.factory import LLMServiceFactory
    
    service = None
    try:
        service = LLMServiceFactory.get_instance()
        yield service
    finally:
        if service:
            await service.close()

async def test_llm_service():
    """Test the LLM service with a simple chat completion."""
    print("Testing LLM service...")
    print(f"Using model: {os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')}")
    
    async with get_llm_service() as llm_service:
        # Test a simple chat completion
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, can you tell me a short joke?"}
        ]
        
        print("\nSending request to LLM...")
        response_text = ""
        
        try:
            async for chunk in llm_service.generate(messages):
                if isinstance(chunk, str):
                    response_text += chunk
                    print(chunk, end="", flush=True)
                else:
                    response_text += chunk.content
                    print(chunk.content, end="", flush=True)
            
            print("\n\nTest completed successfully!")
            return 0
        except Exception as e:
            print(f"\nError during LLM service test: {str(e)}", file=sys.stderr)
            return 1

def main():
    """Run the test and exit with appropriate status code."""
    try:
        exit_code = asyncio.run(test_llm_service())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        exit_code = 130  # SIGINT exit code
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}", file=sys.stderr)
        exit_code = 1
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
