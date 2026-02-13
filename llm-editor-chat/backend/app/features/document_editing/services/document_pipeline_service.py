from typing import Dict, Any, Optional, Tuple
import os
import sys
import json

# Import from the document_editing feature
from app.features.document_editing.services.document_pipeline import DocumentPipeline, API_KEY  # Updated import path

class DocumentPipelineService:
    """Document pipeline service for intelligent section finding and editing"""
    
    # Singleton instance
    _instance = None
    _pipeline = None
    
    @classmethod
    def get_instance(cls) -> 'DocumentPipelineService':
        """Get or create the singleton instance"""
        if cls._instance is None:
            cls._instance = DocumentPipelineService()
        return cls._instance
    
    def __init__(self):
        """Initialize the document pipeline service"""
        if self._pipeline is None:
            self._pipeline = DocumentPipeline(API_KEY)
    
    def process_document(self, file_path: str, prompt: str) -> Dict[str, Any]:
        """Process a document through the pipeline
        
        Args:
            file_path: Path to the document to process
            prompt: The user's prompt for both section finding and editing
            
        Returns:
            Dict containing the processing results and status
        """
        try:
            # Verify the file exists and has content
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "message": f"Error: File not found at {file_path}",
                    "error": "File not found"
                }
                
            # Check if file has content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if not content or content.strip() == "":
                return {
                    "success": False,
                    "message": "Error: The document is empty",
                    "error": "Empty document"
                }
            
            # Process the document using the pipeline
            self._pipeline.process_document(file_path, prompt)
            
            # Read the updated content from the file
            with open(file_path, 'r', encoding='utf-8') as f:
                updated_content = f.read()
            
            return {
                "success": True,
                "message": "Document processed successfully",
                "prompt": prompt,
                "updated_content": updated_content  # Include the updated content in the response
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Error processing document: {str(e)}",
                "error": str(e)
            }
    
    def should_use_pipeline(self, message: str, editor_content: Optional[str], selected_text: Optional[str]) -> bool:
        """Determine if the document pipeline should be used
        
        Args:
            message: The user's message
            editor_content: The editor content
            selected_text: The selected text
            
        Returns:
            True if the pipeline should be used, False otherwise
        """
        # Log inputs for debugging
        print(f"\nDebug - Document Pipeline Activation Check:")
        print(f"  Message: '{message}'")
        print(f"  Has editor content: {bool(editor_content and len(editor_content.strip()) > 0)}")
        print(f"  Has selected text: {bool(selected_text and len(selected_text.strip()) > 0)}")
        
        # If there's no selected text and there is editor content, use the pipeline
        if not (selected_text and len(selected_text.strip()) > 0) and editor_content and len(editor_content.strip()) > 0:
            # Check if the message seems like an editing request
            edit_indicators = [
                "edit", "change", "modify", "update", "revise", "rewrite",
                "add", "insert", "append", "remove", "delete", "fix",
                "improve", "enhance", "refine", "adjust", "correct", "make",
                "create", "write", "draft", "generate", "summarize"
            ]
            
            # Check if any edit indicator is in the message
            should_use = any(indicator in message.lower() for indicator in edit_indicators)
            
            # Log decision
            print(f"  Decision: {should_use}")
            if should_use:
                print(f"  Activating pipeline: Found editing indicator in message")
            else:
                print(f"  Not activating pipeline: No editing indicator found in message")
                
            return should_use
        
        # Log reason for not using pipeline
        if selected_text and len(selected_text.strip()) > 0:
            print(f"  Not activating pipeline: Text is already selected")
        elif not (editor_content and len(editor_content.strip()) > 0):
            print(f"  Not activating pipeline: No editor content")
            
        return False
    
    def save_temp_file(self, content: str) -> Tuple[str, bool, str]:
        """Save content to a temporary file for processing
        
        Args:
            content: The content to save
            
        Returns:
            Tuple[str, bool, str]: (file_path, success, message)
        """
        try:
            # Create a temporary directory if it doesn't exist
            # Updated path to account for new directory structure
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate a unique filename
            import uuid
            temp_file_path = os.path.join(temp_dir, f"temp_doc_{uuid.uuid4()}.md")
            
            # Save the content
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return temp_file_path, True, "Content saved to temporary file"
        except Exception as e:
            return "", False, f"Error saving temporary file: {str(e)}"

    async def process_jsonnode(self, request: Any) -> Dict[str, Any]:
        """Process a JSON node through the pipeline
        
        Args:
            request: ChatRequest object containing the request data
            
        Returns:
            Dict containing the processing results
        """
        # Access request attributes directly since it's a Pydantic model
        message = request.message if hasattr(request, 'message') else ""
        editor_content = request.editor_content if hasattr(request, 'editor_content') else ""
        selected_text = request.selected_text if hasattr(request, 'selected_text') else ""
        # 把request.selected_nodes_info中的id提取出来，变成列表
        selected_nodes_info = request.selected_nodes_info if hasattr(request, 'selected_nodes_info') else []
        selected_nodes_ids = [node['attrs']['id'] for node in selected_nodes_info]
        chat_history = request.chat_history if hasattr(request, 'chat_history') else []
        
        try:
            jsonnode = json.loads(editor_content) if editor_content else {}
            result = await self._pipeline.process_jsonnode(jsonnode, message, selected_text, selected_nodes_ids, chat_history=chat_history)
            return {
                "success": True,
                "result": result,
                "message": "Successfully processed JSON node"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error processing JSON node: {str(e)}"
            }
                
