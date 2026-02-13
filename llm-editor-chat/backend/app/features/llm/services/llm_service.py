"""LLM service module for streaming responses and utility functions.

This module provides functions for streaming LLM responses and processing LLM outputs.
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Union, Tuple, Literal
import asyncio
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import os
from dotenv import load_dotenv
from pathlib import Path
import logging

from app.features.intent_analysis.services.top_level_intent_service import identify_top_level_intent, TopLevelIntent
from app.features.intent_analysis.services.intent_service import identify_document_intent, DocumentIntent
# Import DocumentPipelineService lazily to avoid circular imports

logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent.parent.parent.parent.parent / '.env'
load_dotenv(env_path)
default_api_key = os.getenv("OPENAI_API_KEY")
if default_api_key is None:
    logger.warning("OPENAI_API_KEY environment variable not found, will rely on user-provided API keys")
    default_api_key = ""

# Load editor actions config
_ACTIONS_CONFIG_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "shared" / "editor_actions.json"
with open(_ACTIONS_CONFIG_PATH, encoding="utf-8") as _f:
    _EDITOR_ACTIONS = json.load(_f).get("actions", {})

class StreamingCallbackHandler(StreamingStdOutCallbackHandler):
    """Custom streaming callback handler for LLM responses."""
    def __init__(self, queue):
        super().__init__()
        self.tokens = []
        self.queue = queue
        
    def on_llm_new_token(self, token: str, **kwargs):
        self.tokens.append(token)
        # Put new token into queue for real-time processing
        try:
            self.queue.put_nowait(token)
        except Exception as e:
            logger.error(f"Error adding token to queue: {e}", exc_info=True)
        
    def get_tokens(self):
        return self.tokens

def run_document_pipeline(user_message: str, editor_content: Optional[str], selected_text: Optional[str]) -> Tuple[bool, List[Dict[str, Any]]]:
    """Extracted document pipeline logic from stream_llm_response."""
    # Import DocumentPipelineService lazily to avoid circular imports
    from app.features.document_editing.services.document_pipeline_service import DocumentPipelineService
    
    msgs: List[Dict[str, Any]] = []
    pipeline_service = DocumentPipelineService.get_instance()
    #use_pipeline = pipeline_service.should_use_pipeline(user_message, editor_content, selected_text)
    use_pipeline = True # always use pipeline
    if use_pipeline and editor_content:
        file_path, success, message = pipeline_service.save_temp_file(editor_content)
        if success:
            msgs.append({"type":"thinking","content":"Processing document with intelligent section finding..."})
            result = pipeline_service.process_document(file_path, user_message)
            if result.get("success"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    updated_content = f.read()
                msgs.append({"type":"thinking","content":"Document processed successfully. Applying changes..."})
                action = {"type": _EDITOR_ACTIONS.get("replace_text", {}).get("type", "replace-text"), "payload":{"content":updated_content}}
                msgs.append({"type":"action","content":"Document has been updated with your changes.","action":action})
                return True, msgs
            else:
                msgs.append({"type":"thinking","content":f"Section finding encountered an issue: {result.get('message')}. Falling back to standard processing..."})
        else:
            msgs.append({"type":"thinking","content":f"Could not save temporary file: {message}. Falling back to standard processing..."})
    return False, msgs

def extract_actual_content(response: str) -> str:
    """Extract the actual content from a complete LLM response.
    
    Filters out analysis/thinking process, keeping only the actual content.
    Prioritizes content within <CONTENT> tags, then tries other methods.
    
    Args:
        response: The complete response text from the LLM
    
    Returns:
        The extracted actual content
    """
    # Try to find content within <CONTENT> tags
    content_match = re.search(r'<CONTENT>(.*?)</CONTENT>', response, re.DOTALL)
    if content_match:
        return content_match.group(1).strip()
    
    # Try to find content after "Here's the content:" or similar phrases
    content_marker_match = re.search(r'(?:Here\'s the content:|Here is the content:|Content:)(.*)', response, re.DOTALL)
    if content_marker_match:
        return content_marker_match.group(1).strip()
    
    # Try to find content after a line of dashes or stars (common separator)
    separator_match = re.search(r'(?:---|===|\*\*\*)(.*)', response, re.DOTALL)
    if separator_match:
        return separator_match.group(1).strip()
    
    # If no specific content markers are found, remove common prefixes
    cleaned = re.sub(r'^(?:I\'ll|Let me|Here\'s|I\'ve|I have|I will|I can|I\'m going to).*?:', '', response, flags=re.IGNORECASE)
    
    # If the response starts with a thinking/analysis section, try to find where the actual content begins
    thinking_markers = [
        r'First, let\'s analyze',
        r'Let me think about',
        r'I\'ll approach this',
        r'To solve this',
        r'My approach will be',
        r'Let\'s break this down',
    ]
    
    for marker in thinking_markers:
        if re.search(marker, cleaned, re.IGNORECASE):
            # Try to find where the thinking ends and content begins
            sections = re.split(r'(?:Now, |Finally, |Here\'s |So, |Therefore, )', cleaned, maxsplit=1)
            if len(sections) > 1:
                return sections[1].strip()
    
    # If all else fails, return the original response
    return response.strip()

def build_simple_insert_action(response: str, position: Literal['cursor', 'start', 'end'] = 'cursor') -> Dict[str, Any]:
    """Build a simple insert action, adding a newline based on paragraph count.
    
    If the response has only one paragraph, insert directly; if multiple paragraphs,
    add a newline before inserting.
    
    Args:
        response: The LLM-generated response text
        position: Where to insert the content ('cursor', 'start', or 'end')
    
    Returns:
        A dictionary containing the insert action
    """
    # Count paragraphs (non-empty lines)
    paragraphs = [p for p in response.split('\n') if p.strip()]
    
    # Determine action type based on position
    action_type = _EDITOR_ACTIONS.get("insert_text", {}).get("type", "insert-text")
    if position == 'start':
        action_type = _EDITOR_ACTIONS.get("insert_at_start", {}).get("type", "insert-at-start")
    elif position == 'end':
        action_type = _EDITOR_ACTIONS.get("insert_at_end", {}).get("type", "insert-at-end")
    
    # If multiple paragraphs, add a newline before the content
    content = response
    if len(paragraphs) > 1 and not response.startswith('\n'):
        content = '\n' + response
    
    return {
        "type": action_type,
        "payload": {"content": content}
    }

def create_langchain_chat_model(model: str, temperature: float, handler: StreamingCallbackHandler, custom_api_key: Optional[str] = None) -> ChatOpenAI:
    """Create a LangChain chat model instance.
    
    Args:
        model: Model name
        temperature: Temperature parameter
        handler: Streaming callback handler
        custom_api_key: Optional custom API key to use instead of the default
    
    Returns:
        ChatOpenAI instance
    """
    # For default OpenAI models, always use the default API key from config
    # For custom models (like Claude), use the provided API key
    default_models = ["gpt-4o", "gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]
    
    if model in default_models:
        # Always use the default API key for default OpenAI models
        api_key_to_use = default_api_key
    else:
        # For non-default models (like Claude), use the custom API key if provided
        api_key_to_use = custom_api_key if custom_api_key else default_api_key
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        streaming=True,
        callbacks=[handler],
        api_key=api_key_to_use
    )

async def stream_llm_response(
    system_prompt: str,
    user_message: str,
    editor_content: Optional[str] = None,
    selected_text: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    top_level_intent: Optional[TopLevelIntent] = None,
    second_level_intent: Optional[Any] = None,
    api_key: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    General LLM streaming response handler function.
    
    Args:
        system_prompt: System prompt
        user_message: User message
        editor_content: Editor content (optional)
        selected_text: Selected text (optional)
        model: Model name
        temperature: Temperature parameter
        top_level_intent: Top-level intent (optional)
        second_level_intent: Second-level intent (optional)
        api_key: Custom API key to use for the LLM provider (optional)
    
    Yields:
        Dict containing message type and content
    """
    try:
        # Check if we should use the document pipeline
        use_pipeline, pipeline_msgs = run_document_pipeline(user_message, editor_content, selected_text)
        if use_pipeline:
            for msg in pipeline_msgs:
                yield msg
            return
        
        # Create queue for streaming tokens
        queue = asyncio.Queue()
        
        # Create streaming callback handler
        handler = StreamingCallbackHandler(queue)
        
        # Create LangChain chat model
        # If a custom model is specified, use it, otherwise use the default model
        model_to_use = model if model else "gpt-4.1"
        
        # Log which model is being used
        logger.info(f"Using model: {model_to_use}")
        if model_to_use.startswith("claude"):
            logger.info("Using Claude model with custom API key")
        else:
            logger.info("Using OpenAI model with default API key")
        client = create_langchain_chat_model(model_to_use, temperature, handler, api_key)
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add context information if available
        context_parts = []
        if editor_content:
            context_parts.append(f"EDITOR CONTENT:\n{editor_content}")
        if selected_text:
            context_parts.append(f"SELECTED TEXT:\n{selected_text}")
        
        if context_parts:
            context_message = "\n\n".join(context_parts)
            messages.append({"role": "user", "content": f"CONTEXT:\n{context_message}"})
        
        # Add user message
        messages.append({"role": "user", "content": user_message})
        
        # Convert messages to LangChain format
        langchain_messages = []
        for msg in messages:
            if msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))
            else:
                langchain_messages.append(HumanMessage(content=msg["content"]))
        
        # Start generating response
        task = asyncio.create_task(client.ainvoke(langchain_messages))
        
        # Define callback for task completion
        def done_callback(t):
            try:
                # Put None in queue to signal end of streaming
                queue.put_nowait(None)
            except Exception as e:
                logger.error(f"Error in done callback: {e}", exc_info=True)
        
        # Set callback
        task.add_done_callback(done_callback)
        
        # Send initial thinking message
        yield {"type": "thinking", "content": "Thinking..."}
        
        # Process streaming tokens
        thinking_buffer = ""
        current_thinking = ""
        action_pattern = re.compile(r'\[ACTION\](.*?)\[/ACTION\]', re.DOTALL)
        
        while True:
            try:
                # Get next token with timeout
                token = await asyncio.wait_for(queue.get(), timeout=0.1)
                
                # Check if end of streaming
                if token is None:
                    break
                
                # Add token to thinking buffer
                thinking_buffer += token
                
                # Check if there is a complete thinking block (at least 50 characters)
                if len(thinking_buffer) >= 50 and "\n" in thinking_buffer:
                    # Split by newline to get complete thoughts
                    parts = thinking_buffer.split("\n")
                    complete_thoughts = parts[:-1]
                    thinking_buffer = parts[-1]
                    
                    # Join complete thoughts
                    clean_thinking = "\n".join(complete_thoughts)
                    
                    # Remove any ACTION blocks
                    clean_thinking = re.sub(r'\[ACTION\].*?\[/ACTION\]', '', clean_thinking, flags=re.DOTALL)
                    
                    # Remove partial ACTION block (only start tag)
                    clean_thinking = re.sub(r'\[ACTION\].*', '', clean_thinking, flags=re.DOTALL)
                    
                    # Remove partial ACTION block (only end tag)
                    clean_thinking = re.sub(r'.*\[/ACTION\]', '', clean_thinking, flags=re.DOTALL)
                    
                    if clean_thinking.strip():
                        # Send thinking message
                        current_thinking = clean_thinking.strip()
                        yield {"type": "message", "content": current_thinking}
                    
                    # Reset thinking buffer
                    thinking_buffer = ""
                
                # Check if there is a complete ACTION block
                action_matches = action_pattern.findall(thinking_buffer)
                if action_matches:
                    for action_content in action_matches:
                        try:
                            # Parse action content as JSON
                            action_json = json.loads(action_content.strip())
                            
                            # Send action message
                            yield {"type": "action", "content": "Content generation completed, ready to be inserted into the editor.", "action": action_json}
                            
                            # Remove processed action from buffer
                            thinking_buffer = re.sub(r'\[ACTION\].*?\[/ACTION\]', '', thinking_buffer, flags=re.DOTALL)
                        except json.JSONDecodeError:
                            # If JSON parsing fails, just continue
                            logger.warning(f"Failed to parse action JSON: {action_content}")
            except asyncio.TimeoutError:
                # No token available, just continue
                pass
            except Exception as e:
                # Log error and continue
                logger.error(f"Error processing token: {e}", exc_info=True)
        
        # Process any remaining thinking buffer
        if thinking_buffer.strip():
            # Remove any ACTION blocks
            clean_thinking = re.sub(r'\[ACTION\].*?\[/ACTION\]', '', thinking_buffer, flags=re.DOTALL)
            clean_thinking = re.sub(r'\[ACTION\].*', '', clean_thinking, flags=re.DOTALL)
            clean_thinking = re.sub(r'.*\[/ACTION\]', '', clean_thinking, flags=re.DOTALL)
            
            if clean_thinking.strip():
                # Send final thinking message
                yield {"type": "message", "content": clean_thinking.strip()}
        
        # Wait for the model task to complete
        await task
        
        # Get the final response from the model
        response = task.result()
        
        # Check if there are any ACTION blocks in the final response that weren't caught by streaming
        content = response.content
        action_matches = action_pattern.findall(content)
        
        if action_matches:
            for action_content in action_matches:
                try:
                    # Parse action content as JSON
                    action_json = json.loads(action_content.strip())
                    
                    # Send action message
                    yield {"type": "action", "content": "Content generation completed, ready to be inserted into the editor.", "action": action_json}
                except json.JSONDecodeError:
                    # If JSON parsing fails, just continue
                    logger.warning(f"Failed to parse action JSON: {action_content}")
        
        # Send final message without ACTION blocks
        clean_content = re.sub(r'\[ACTION\].*?\[/ACTION\]', '', content, flags=re.DOTALL)
        if clean_content.strip() and clean_content.strip() != current_thinking:
            # Only send if it's different from the last thinking message
            yield {"type": "message", "content": clean_content.strip()}
    except Exception as e:
        yield {"type": "error", "content": f"Error occurred: {str(e)}"}
