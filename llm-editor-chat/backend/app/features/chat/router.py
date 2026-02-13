from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import asyncio
import contextvars
import re
import os
import logging

from tempfile import NamedTemporaryFile

# Define context variable for storing top-level intent
current_top_intent = contextvars.ContextVar('current_top_intent', default=None)

def get_current_intent():
    """Utility function to get the current top-level intent from context.
    
    Returns:
        The current top-level intent or None if not set.
    """
    return current_top_intent.get()

# 配置日志记录
logger = logging.getLogger(__name__)

# Import shared service modules
from app.features.llm.services.llm_service import stream_llm_response
from app.features.intent_analysis.services.top_level_intent_service import identify_top_level_intent
from app.features.intent_analysis.services.intent_service import identify_document_intent
from app.features.intent_analysis.services.create_new_intent_service import identify_create_new_intent, CreateNewIntent
from app.features.intent_analysis.services.modify_existing_intent_service import identify_modify_existing_intent, ModifyExistingIntent, confirm_modify_intent
from app.features.intent_analysis.services.create_new_content_service import confirm_create_new_intent, generate_new_content, generate_content_explanation, format_content_for_insertion, analyze_content_structure
from app.features.document_structure.services.explanation_service import generate_modification_explanation
from app.models.editor_actions import create_replace_all_action
# PPT service has been moved to features directory
from app.features.application.services.ppt_service import stream_ppt_generation
from app.features.document_editing.services.document_pipeline_service import DocumentPipelineService  # Updated import path
from app.features.intent_analysis.services.insert_image_intent_service import identify_insert_image_intent, InsertImageIntent
from app.features.document_editing.services.target_service import identify_text_target, identify_modify_target

router = APIRouter(prefix="/chat", tags=["chat"])
# Removed StreamingCallbackHandler class, now using the version in llm_service

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    editor_content: Optional[str] = None
    editor_content_json: Optional[str] = None
    editor_content_html: Optional[str] = None
    selected_text: Optional[str] = None
    file_path: Optional[str] = None  # 单文件路径（向后兼容）
    file_paths: Optional[str] = None  # 多文件路径的JSON字符串
    selected_nodes_info: Optional[List[Dict[str, Any]]] = None
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    document_word_count: Optional[int] = None  # 文档单词数
    document_char_count: Optional[int] = None  # 文档字符数
    chat_history: Optional[List[Dict[str, str]]] = None  # 聊天历史记录
    model_id: Optional[str] = None  # 用户选择的LLM模型ID
    api_key: Optional[str] = None  # 用户提供的API密钥

@router.post("/upload-file")
async def upload_file(file: UploadFile = File(...)):
    """Upload file endpoint for handling file attachments (legacy single file support)"""
    try:
        # Create a temporary directory if it doesn't exist
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate a unique filename
        file_extension = os.path.splitext(file.filename)[1]
        temp_file_path = os.path.join(temp_dir, f"upload_{asyncio.current_task().get_name()}{file_extension}")
        
        # Save the uploaded file
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        return {"file_path": temp_file_path, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.post("/upload-files")
async def upload_files(files: list[UploadFile] = File(...)):
    """Upload multiple files endpoint for handling multiple file attachments"""
    try:
        # Create a temporary directory if it doesn't exist
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        results = []
        task_id = asyncio.current_task().get_name()
        
        for i, file in enumerate(files):
            # Generate a unique filename for each file
            file_extension = os.path.splitext(file.filename)[1]
            temp_file_path = os.path.join(temp_dir, f"upload_{task_id}_{i}{file_extension}")
            
            # Save the uploaded file
            with open(temp_file_path, "wb") as buffer:
                buffer.write(await file.read())
            
            results.append({
                "file_path": temp_file_path, 
                "filename": file.filename
            })
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multiple files upload failed: {str(e)}")

@router.post("/stream")
async def stream_chat(request: ChatRequest):
    """Streaming chat API endpoint"""
    
    # 处理编辑器内容格式 - 支持新的 JSON 格式和旧的 HTML 格式
    editor_content = None
    editor_content_format = "unknown"
    
    # 检查是否提供了 JSON 格式的编辑器内容
    if request.editor_content and request.editor_content.strip():
        try:
            # 尝试解析 JSON 格式
            import json
            json.loads(request.editor_content)
            editor_content = request.editor_content
            editor_content_format = "json"
            logger.info("使用 JSON 格式的编辑器内容")
        except json.JSONDecodeError:
            # 如果不是有效的 JSON，假设它是 HTML 格式
            editor_content = request.editor_content
            editor_content_format = "html"
            logger.info("使用 HTML 格式的编辑器内容（从 editor_content 字段）")
    
    # 如果没有有效的 JSON 内容但有 HTML 内容，使用 HTML 内容
    if (editor_content_format == "unknown" or editor_content_format == "html") and request.editor_content_html:
        editor_content = request.editor_content_html
        editor_content_format = "html"
        logger.info("使用 HTML 格式的编辑器内容（从 editor_content_html 字段）")
    
    # 记录内容格式信息
    if editor_content:
        logger.info(f"编辑器内容格式: {editor_content_format}")
    else:
        logger.info("未提供编辑器内容")
        
    # 更新请求对象中的编辑器内容，确保后续处理使用正确的内容
    request.editor_content = editor_content
    
    async def generate():
        try:
            # Send initial "thinking" message
            yield f"data: {json.dumps({'type': 'thinking', 'content': 'Figuring out what you want...'})}\n\n"
            
            # Step 1: Identify top-level intent
            top_intent = await identify_top_level_intent(request.message)
            
            # Store top_intent in context variable for access by other functions
            current_top_intent.set(top_intent)
            
            # Choose different processing paths based on top-level intent
            if top_intent.intent_type == "create_new" and top_intent.confidence > 0.6:
                # For content creation, we need to identify document type
                # Use welcome_message from top_intent if available, otherwise use default message
                welcome_msg = (
                    top_intent.additional_info.get('welcome_message') 
                    if top_intent.additional_info and top_intent.additional_info.get('welcome_message') 
                    else 'Got your request. Figuring out the document type...'
                )
                yield f"data: {json.dumps({'type': 'thinking', 'content': welcome_msg})}\n\n"
                
                # Step 2: Get document-specific intent
                # doc_intent = await identify_document_intent(request.message)
                
                # 二级意图：针对 create_new 进一步分析，传入文件路径以改进意图识别
                create_new_intent = await identify_create_new_intent(request.message, file_path=request.file_path)
                # 根据 document_type 路由
                if 'powerpoint' in create_new_intent.document_type.lower() and create_new_intent.confidence > 0.6:
                    # PPT generation path
                    yield f"data: {json.dumps({'type': 'thinking', 'content': 'Detected PPT creation request. Using specialized PPT generator...'})}\n\n"
                    
                    # Use specialized PPT generation module
                    async for event in stream_ppt_generation(
                        user_message=request.message,
                        editor_content=request.editor_content,
                        file_path=request.file_path,
                        create_new_intent=create_new_intent
                    ):
                        # Format event as SSE format
                        yield f"data: {json.dumps(event)}\n\n"
                else:
                    # Generic content creation (not PPT)
                    # Get detailed content creation intent description
                    create_intent_description = await confirm_create_new_intent(request.message)
                    yield f"data: {json.dumps({'type': 'thinking', 'content': f'{create_intent_description}'})}\n\n"
                    
                    try:
                        # Generate new content using the specialized service
                        generated_content = await generate_new_content(
                            user_message=request.message,
                            create_new_intent=create_new_intent.model_dump() if create_new_intent else {}
                        )
                        
                        if generated_content:
                            # Format content for proper insertion
                            formatted_content = format_content_for_insertion(generated_content)
                            
                            # Analyze content structure for better logging and explanation
                            content_analysis = analyze_content_structure(formatted_content)
                            
                            # Get correct action type from editor_actions.json
                            from app.features.llm.services.router import _EDITOR_ACTIONS
                            
                            # Create insert-text action
                            action = {
                                "type": _EDITOR_ACTIONS.get("insert_text", {}).get("type", "insert-text"),
                                "payload": {
                                    "content": formatted_content,
                                    "position": "cursor"
                                }
                            }
                            
                            # Log action object details with content analysis
                            logger.info(f"Generated action object: {json.dumps(action)}")
                            logger.info(f"Action type: {action['type']}, Content analysis: {content_analysis}")
                            logger.info(f"Content type: {content_analysis['content_type']}, Word count: {content_analysis['word_count']}, Reading time: ~{content_analysis['estimated_reading_time']} min")
                            
                            # Generate explanation
                            explanation = 'New content created'
                            try:
                                explanation = await generate_content_explanation(
                                    user_request=request.message,
                                    generated_content=formatted_content
                                )
                                
                                # Send explanation as thinking message
                                explanation_msg = json.dumps({'type': 'thinking', 'content': explanation})
                                logger.info(f"Sending explanation message: {explanation_msg}")
                                yield f"data: {explanation_msg}\n\n"
                            except Exception as e:
                                logger.error(f"Error generating explanation: {e}")
                            
                            # Prepare and send action message
                            action_msg = json.dumps({'type': 'action', 'content': explanation, 'action': action})
                            logger.info(f"Message sent to frontend: {action_msg}")
                            
                            yield f"data: {action_msg}\n\n"
                            return
                        else:
                            # If content generation fails, log error and fallback
                            logger.error("Content generation returned empty result")
                            yield f"data: {json.dumps({'type': 'thinking', 'content': 'Content generation failed. Using fallback approach...'})}\n\n"
                            
                            # Fallback to standard LLM processing if content generation fails
                            yield f"data: {json.dumps({'type': 'thinking', 'content': 'Using standard LLM processing for content creation...'})}\n\n"
                            
                            # Use fallback system prompt
                            system_prompt = """You are a document creation assistant. The user wants to create new content.
                            Generate high-quality content that directly fulfills the user's request.
                            Focus on creating well-structured, engaging content appropriate for the requested type.
                            """
                            
                            async for event in stream_llm_response(
                                system_prompt=system_prompt,
                                user_message=request.message,
                                editor_content=request.editor_content,
                                selected_text=request.selected_text,
                                top_level_intent=top_intent,
                                second_level_intent=create_new_intent
                            ):
                                yield f"data: {json.dumps(event)}\n\n"
                    except Exception as e:
                        # Capture any unhandled exceptions in content generation
                        logger.error(f"Error in content generation: {str(e)}")
                        yield f"data: {json.dumps({'type': 'thinking', 'content': f'Content generation error: {str(e)}. Using fallback approach...'})}\n\n"
                        
                        # Fallback to standard LLM processing if content generation fails
                        yield f"data: {json.dumps({'type': 'thinking', 'content': 'Using standard LLM processing for content creation...'})}\n\n"
                        
                        # Use fallback system prompt
                        system_prompt = """You are a document creation assistant. The user wants to create new content.
                        Generate high-quality content that directly fulfills the user's request.
                        Focus on creating well-structured, engaging content appropriate for the requested type.
                        """
                        
                        async for event in stream_llm_response(
                            system_prompt=system_prompt,
                            user_message=request.message,
                            editor_content=request.editor_content,
                            selected_text=request.selected_text,
                            top_level_intent=top_intent,
                            second_level_intent=create_new_intent
                        ):
                            yield f"data: {json.dumps(event)}\n\n"
            
            # other treated as modify_existing
            elif (top_intent.intent_type == "modify_existing" or top_intent.intent_type == "other") and top_intent.confidence > 0.6 and request.editor_content:
                # Get detailed modification intent description
                modify_intent_description = await confirm_modify_intent(request.message)
                yield f"data: {json.dumps({'type': 'thinking', 'content': f'{modify_intent_description}'})}\n\n"
                
                # Use DocumentPipeline to process document modification requests
                # yield f"data: {json.dumps({'type': 'thinking', 'content': 'Detected modification request. Using document pipeline for intelligent processing...'})}\n\n"
                
                # Initialize DocumentPipelineService
                pipeline_service = DocumentPipelineService.get_instance()
                
                # TODO: Always force pipeline usage
                try:
                    # 直接调用处理服务，不需要保存临时文件
                    result = await pipeline_service.process_jsonnode(request)
                    
                    if result.get("success", False):
                        # Send success message
                        # yield f"data: {json.dumps({'type': 'thinking', 'content': 'Document processed successfully, applying changes...'})}\n\n"
                        
                        # Send update editor content action
                        # Get correct action type from editor_actions.json
                        from app.features.llm.services.router import _EDITOR_ACTIONS
                        
                        # Get current editor content length
                        json_update = result['result'].get('path_updates', [])
                        json_update_str = json.dumps(json_update, ensure_ascii=False)
                        
                        editor_content_length = len(json_update_str) if json_update_str else 0
                        
                        # Log detailed information
                        logger.info(f"Editor content length: {editor_content_length}")
                        
                        # Use from and to properties instead of start and end to match frontend expected property names
                        # Ensure to value does not exceed actual document length
                        action = {
                            "type": _EDITOR_ACTIONS.get("replace_text", {}).get("type", "replace-text"), 
                            "payload": {
                                "content": json_update_str, 
                                "from": 0, 
                                "to": editor_content_length
                            }
                        }
                        
                        # Log action object details
                        logger.info(f"Generated action object: {json.dumps(action)}")                            
                        logger.info(f"Action type: {action['type']}, Content length: {len(action['payload']['content']) if 'content' in action['payload'] else 0}")
                        
                        # 生成解释性反馈
                        explanation = 'Document updated'
                        try:
                            # 获取原始内容和修改后的内容
                            original_content = request.editor_content if request.editor_content else ""
                            modified_content = json_update_str if json_update_str else ""
                            
                            # 生成解释性反馈
                            explanation = await generate_modification_explanation(
                                original_content=original_content,
                                modified_content=modified_content,
                                user_request=request.message
                            )
                            
                            # 发送解释性反馈作为thinking消息
                            explanation_msg = json.dumps({'type': 'thinking', 'content': explanation})
                            logger.info(f"Sending explanation message: {explanation_msg}")
                            #yield f"data: {explanation_msg}\n\n"
                        except Exception as e:
                            logger.error(f"Error generating explanation: {e}")
                        
                        # 准备并发送动作消息
                        action_msg = json.dumps({'type': 'action', 'content': explanation, 'action': action})
                        logger.info(f"Message sent to frontend: {action_msg}")
                        
                        yield f"data: {action_msg}\n\n"
                        return
                    else:
                        # If processing fails, log error and fallback to standard processing
                        error_message = result.get("message", "Unknown error in document processing")
                        logger.error(f"Document pipeline error: {error_message}")
                        yield f"data: {json.dumps({'type': 'thinking', 'content': f'处理文档时出错: {error_message}. 回退到标准处理...'})}\n\n"
                except Exception as e:
                    # Capture any unhandled exceptions
                    logger.error(f"Error in document pipeline: {str(e)}")
                    yield f"data: {json.dumps({'type': 'thinking', 'content': f'处理文档时出错: {str(e)}. 回退到标准处理...'})}\n\n"
                
                # If pipeline is not applicable or processing fails, fallback to standard LLM processing
                yield f"data: {json.dumps({'type': 'thinking', 'content': 'Using standard LLM processing for your request...'})}\n\n"
                
                # Use generic system prompt
                system_prompt = """You are an AI assistant helping with text editing tasks. 
                Analyze the user's request and the current document content, then provide appropriate edits or suggestions.
                Focus on making targeted changes that address the user's specific request while maintaining the document's overall style and structure."""
                
                # 调用通用流式响应
                async for event in stream_llm_response(
                    system_prompt=system_prompt,
                    user_message=request.message,
                    editor_content=request.editor_content,
                    selected_text=request.selected_text,
                    top_level_intent=top_intent
                ):
                    yield f"data: {json.dumps(event)}\n\n"
                return
            
            elif top_intent.intent_type == "insert_image" and top_intent.confidence > 0.6:
                # 二级意图：解析图片类型
                # Use welcome_message from top_intent if available, otherwise use default message
                welcome_msg = (
                    top_intent.additional_info.get('welcome_message') 
                    if top_intent.additional_info and top_intent.additional_info.get('welcome_message') 
                    else 'Detected image insertion request. Classifying image type...'
                )
                yield f"data: {json.dumps({'type': 'thinking', 'content': welcome_msg})}\n\n"
                img_intent = await identify_insert_image_intent(request.message)
                yield f"data: {json.dumps({'type': 'thinking', 'content': f'Image intent: {img_intent.image_type}'})}\n\n"
                # 根据图片类型不同处理
                # 创建图像处理器实例
                from app.features.processing.image_insertion_processor import ImageInsertionProcessor
                processor = ImageInsertionProcessor()
                
                # 根据图像类型发送处理中消息
                if img_intent.image_type == "aesthetic":
                    yield f"data: {json.dumps({'type': 'message', 'content': 'Generating aesthetic image... This may take a moment.'})}\n\n"
                    image_type = "aesthetic"
                else:  # conceptual
                    yield f"data: {json.dumps({'type': 'message', 'content': 'Generating conceptual diagram... This may take a moment.'})}\n\n"
                    image_type = "conceptual"
                
                try:
                    # 处理图像生成请求
                    action = await processor.process_image_insertion(
                        message=request.message,
                        image_type=image_type,
                        position="cursor"  # 默认在光标位置插入
                    )
                    
                    # 检查是否成功生成图像
                    if "type" in action and action["type"] == "error":
                        # 如果生成失败，返回错误消息
                        yield f"data: {json.dumps({'type': 'error', 'content': action['message']})}\n\n"
                    else:
                        # 如果成功，返回编辑器动作和成功消息
                        yield f"data: {json.dumps({'type': 'action', 'action': action})}\n\n"
                        yield f"data: {json.dumps({'type': 'message', 'content': f'Image generated successfully! Inserting at cursor position.'})}\n\n"
                except Exception as e:
                    # 捕获任何未处理的异常
                    error_message = f"Error generating image: {str(e)}"
                    yield f"data: {json.dumps({'type': 'error', 'content': error_message})}\n\n"
            
            elif top_intent.intent_type == "read_file" and top_intent.confidence > 0.6:
                # For file reading and operation requests
                # Use welcome_message from top_intent if available, otherwise use default message
                welcome_msg = (
                    top_intent.additional_info.get('welcome_message') 
                    if top_intent.additional_info and top_intent.additional_info.get('welcome_message') 
                    else 'Detected file reading request. Processing...'
                )
                yield f"data: {json.dumps({'type': 'thinking', 'content': welcome_msg})}\n\n"
                
                # Here you would implement file reading logic
                # For now, we'll just respond with a message
                yield f"data: {json.dumps({'type': 'message', 'content': 'File reading functionality is coming soon. Please stay tuned!'})}\n\n"

            # 专门处理纯问答类型请求
            elif top_intent.intent_type == "question_only" and top_intent.confidence > 0.6:
                # 问答类型 - 使用主线的 stream_llm_response 进行处理
                # Use welcome_message from top_intent if available, otherwise use default message
                welcome_msg = (
                    top_intent.additional_info.get('welcome_message') 
                    if top_intent.additional_info and top_intent.additional_info.get('welcome_message') 
                    else 'Understood. Processing the question...'
                )
                yield f"data: {json.dumps({'type': 'thinking', 'content': welcome_msg})}\n\n"
                
                async for event in stream_llm_response(
                    system_prompt="""You are a helpful document assistant. Answer the user's question clearly and concisely.
+
If the question relates to the current document or selected text, refer to that context in your answer.
+
Focus on providing information only - do not suggest changes to the document unless explicitly asked.
+""",
                    user_message=request.message,
                    editor_content=request.editor_content,
                    selected_text=request.selected_text,
                    top_level_intent=top_intent,
                    second_level_intent=None,
                    model=request.model_id if request.model_id else None,
                    api_key=request.api_key if request.api_key else None
                ):
                    yield f"data: {json.dumps(event)}\n\n"
            
            # 处理其他未分类的请求    
            else:
                # Default path - use LLM service for other unclassified actions
                # This handles other intents that don't fit into specific categories
                system_prompt = """You are a document editing assistant. When a user provides a request, you need to:
1. Briefly outline your approach (keep it concise - just key points)
2. Generate content that meets the user's requirements in a well-structured format

Your response will be automatically processed and inserted into the editor as needed, so focus on producing high-quality content that meets the user's specific needs.
"""
                
                # Use shared service module to handle LLM streaming response
                async for event in stream_llm_response(
                    system_prompt=system_prompt,
                    user_message=request.message,
                    editor_content=request.editor_content,
                    selected_text=request.selected_text,
                    top_level_intent=top_intent,
                    second_level_intent=None,  # 默认分支没有二级意图
                    model=request.model_id if request.model_id else None,
                    api_key=request.api_key if request.api_key else None
                ):
                    # Format event as SSE format
                    yield f"data: {json.dumps(event)}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error occurred: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
