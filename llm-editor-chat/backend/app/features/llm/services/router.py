from typing import List, Dict, Any, Callable, Optional, AsyncGenerator, Union, Tuple, Literal
import asyncio
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv
from pathlib import Path
import logging
logger = logging.getLogger(__name__)
from app.features.intent_analysis.services.top_level_intent_service import identify_top_level_intent, TopLevelIntent
from app.features.intent_analysis.services.intent_service import identify_document_intent, DocumentIntent
from app.features.document_editing.services.document_pipeline_service import DocumentPipelineService  # Updated import path

# Import StreamingCallbackHandler from llm_service to avoid duplication
from app.features.llm.services.llm_service import StreamingCallbackHandler

# Load environment variables
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)
api_key = os.getenv("OPENAI_API_KEY")
if api_key is None:
    raise ValueError("OPENAI_API_KEY environment variable not found")

# Load editor actions config
_ACTIONS_CONFIG_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "shared" / "editor_actions.json"
with open(_ACTIONS_CONFIG_PATH, encoding="utf-8") as _f:
    _EDITOR_ACTIONS = json.load(_f).get("actions", {})

# StreamingCallbackHandler is now imported from llm_service.py

def run_document_pipeline(user_message: str, editor_content: Optional[str], selected_text: Optional[str]) -> Tuple[bool, List[Dict[str, Any]]]:
    """Extracted document pipeline logic from stream_llm_response."""
    msgs: List[Dict[str, Any]] = []
    pipeline_service = DocumentPipelineService.get_instance()
    use_pipeline = pipeline_service.should_use_pipeline(user_message, editor_content, selected_text)
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
    """从LLM的完整响应中提取出真正的内容。
    
    过滤掉分析/思考过程，只保留实际内容。
    优先查找<CONTENT>标签中的内容，如果没有则尝试其他方法。
    
    参数:
    - response: LLM生成的完整响应文本
    
    返回:
    - 提取出的实际内容
    """
    # 首先查找<CONTENT>标签中的内容（优先级最高）
    content_tag_pattern = r'<CONTENT>(\s*[\s\S]*?\s*)</CONTENT>'
    content_matches = re.findall(content_tag_pattern, response, re.DOTALL)
    if content_matches:
        return content_matches[0].strip()
    
    # 如果没有<CONTENT>标签，尝试查找其他常见的内容标记
    content_markers = [
        # 查找HTML或代码块
        (r'```html\s*([\s\S]*?)```', 1),  # HTML代码块
        (r'```markdown\s*([\s\S]*?)```', 1),  # Markdown代码块
        (r'```([\s\S]*?)```', 1),  # 任意代码块
        (r'<p[^>]*>(.*?)</p>', 1),  # HTML段落标签
        
        # 查找内容生成部分
        (r'2\. (?:Content Generation|Generate[\s\S]*?content)[:\s]*([\s\S]*?)(?:3\.|$)', 1),  # 内容生成部分
        (r'Content[:\s]*([\s\S]*?)(?:$|\n\n\d\.)', 1),  # 以Content:开头的部分
        
        # 查找最终结果部分
        (r'Final Result[:\s]*([\s\S]*?)(?:$|\n\n)', 1),  # 最终结果部分
        (r'Result[:\s]*([\s\S]*?)(?:$|\n\n)', 1),  # 结果部分
    ]
    
    # 尝试使用每个标记提取内容
    for pattern, group in content_markers:
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            # 使用第一个匹配结果
            return matches[0].strip()
    
    # 如果没有找到明确的内容标记，尝试基于结构分析
    lines = response.split('\n')
    
    # 检查是否有编号列表格式 (1. xxx, 2. xxx)
    numbered_lines = [i for i, line in enumerate(lines) if re.match(r'^\d+\.\s', line.strip())]
    
    if numbered_lines:
        # 找到最后一个编号后的所有内容
        last_numbered = numbered_lines[-1]
        if last_numbered < len(lines) - 1:
            return '\n'.join(lines[last_numbered+1:]).strip()
    
    # 如果以上方法都失败，返回原始响应的后半部分（假设前半部分是分析）
    half_point = len(response) // 2
    return response[half_point:].strip()

def build_simple_insert_action(response: str, position: Literal['cursor', 'start', 'end'] = 'cursor') -> Dict[str, Any]:
    """构建简单的插入动作，根据段落数决定是否添加空行。
    
    如果响应只有一个段落，直接插入；如果有多个段落，在前面添加空行再插入。
    
    参数:
    - response: LLM生成的响应文本
    
    返回:
    - 包含插入动作的字典
    """
    # 分割段落并过滤空段落
    paragraphs = [p for p in response.split("\n\n") if p.strip()]
    
    # 根据段落数决定是否添加空行
    content = response if len(paragraphs) <= 1 else "\n\n" + response
    
    return {
        "type": _EDITOR_ACTIONS.get("insert_text", {}).get("type", "insert-text"),
        "position": position,
        "payload": {"content": content}
    }

def create_langchain_chat_model(model: str, temperature: float, handler: StreamingCallbackHandler) -> ChatOpenAI:
    """创建 LangChain 聊天模型实例。
    
    参数:
    - model: 模型名称
    - temperature: 温度参数
    - handler: 流式回调处理器
    
    返回:
    - ChatOpenAI 实例
    """
    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=temperature,
        streaming=True,
        callbacks=[handler],
        verbose=True
    )

async def stream_llm_response(
    system_prompt: str,
    user_message: str,
    editor_content: Optional[str] = None,
    selected_text: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    top_level_intent: Optional[TopLevelIntent] = None,
    second_level_intent: Optional[Any] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    通用的LLM流式响应处理函数
    
    参数:
    - system_prompt: 系统提示词
    - user_message: 用户消息
    - editor_content: 编辑器内容（可选）
    - selected_text: 选中的文本（可选）
    - model: 使用的模型名称
    - temperature: 温度参数
    
    返回:
    - 异步生成器，生成流式响应事件
    """
    try:
        # 使用顶层意图识别决定是否使用新流水线
        if top_level_intent is None:
            # 只有在没有传入意图时才调用意图识别
            top_intent = await identify_top_level_intent(user_message)
            yield {"type": "thinking", "content": f"Intent: {top_intent.intent_type} (置信度 {top_intent.confidence:.2f})"}
        else:
            # 使用传入的意图，避免重复调用
            top_intent = top_level_intent
            # yield {"type": "thinking", "content": f"Using provided intent: {top_intent.intent_type} (置信度 {top_intent.confidence:.2f})"}
        
        # 处理简单问答类型（question_only）：只在聊天窗口显示，不插入到编辑器
        if top_intent.intent_type == "question_only":
            # 发送思考消息
            # yield {"type": "thinking", "content": "Processing question without editor changes..."}
            
            # 创建异步队列用于实时处理token
            token_queue = asyncio.Queue()
            
            # 创建流式回调处理器
            handler = StreamingCallbackHandler(token_queue)
            
            # 创建聊天模型
            chat = create_langchain_chat_model(model, temperature, handler)
            
            # 构造消息
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
            
            # 如果有编辑器内容，添加到消息中
            if editor_content:
                messages.append(HumanMessage(content=f"Current editor content (for reference only, do not repeat this content in your answer):\n{editor_content}"))
                
            # 如果有选中文本，添加到消息中
            if selected_text:
                messages.append(HumanMessage(content=f"Selected text:\n{selected_text}"))
            
            # 异步调用模型
            task = asyncio.create_task(chat.ainvoke(messages))
            
            # 设置任务完成回调，确保任务被正确清理
            def done_callback(t):
                try:
                    # 检查任务是否有异常
                    if t.exception() is not None and not isinstance(t.exception(), asyncio.CancelledError):
                        logger.error(f"Task completed with exception: {t.exception()}", exc_info=True)
                except asyncio.CancelledError:
                    logger.warning("Task was cancelled")
                except Exception as e:
                    logger.error(f"Error in done callback: {e}", exc_info=True)
                    
            task.add_done_callback(done_callback)
            
            # 收集完整响应并实时显示
            full_response = ""
            current_chunk = ""
            
            # 处理流式输出
            try:
                while not task.done() or not token_queue.empty():
                    try:
                        # 以非阻塞方式从队列获取token
                        token = await asyncio.wait_for(token_queue.get(), timeout=0.1)
                        full_response += token
                        current_chunk += token
                        
                        # 实时发送消息更新
                        # 在句子结束或换行时清空当前块
                        if token in ['.', '?', '!', '\n']:
                            current_chunk = ""
                            
                        # yield only new token to avoid repeating full content
                        yield {"type": "stream", "content": token}
                    except asyncio.TimeoutError:
                        # 没有可用的token，继续
                        pass
                    except Exception as e:
                        # 记录错误并继续
                        logger.error(f"Error processing token: {e}", exc_info=True)
            except asyncio.CancelledError:
                logger.warning("Stream processing was cancelled")
                # 确保任务被取消
                if not task.done():
                    task.cancel()
                raise  # 重新抛出异常，让调用者知道处理被取消
            except Exception as e:
                logger.error(f"Error in stream processing loop: {e}", exc_info=True)
                # 确保任务被取消
                if not task.done():
                    task.cancel()
            
            # 等待模型任务完成
            try:
                await task
            except asyncio.CancelledError:
                logger.warning("Task await was cancelled")
                raise  # 重新抛出异常
            except Exception as e:
                logger.error(f"Error awaiting task: {e}", exc_info=True)
            
            # Removed final full_response yield to avoid duplicate display when streaming
            # if full_response.strip():
            #     yield {"type": "message", "content": full_response.strip()}
            
            return
            
        # 处理创建新文档意图（create_new）
        if top_intent.intent_type == "create_new":
            # 使用二级意图给出反馈
            doc_type = second_level_intent or 'document'
            # yield {"type": "thinking", "content": f"Creating new {doc_type}..."}
            
            # Create async queue for real-time token processing
            token_queue = asyncio.Queue()
            
            # Send "thinking" message
            yield {"type": "thinking", "content": "Creating content to add..."}
            
            # Create streaming callback handler
            handler = StreamingCallbackHandler(token_queue)
            
            # Create chat model
            chat = create_langchain_chat_model(model, temperature, handler)
            
            # Construct messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
            
            # 对于创建新内容的意图，不添加编辑器现有内容，以避免内容重复
            # 这里故意留空，不添加编辑器内容
                
            # If there is selected text, add it to the messages
            if selected_text:
                messages.append(HumanMessage(content=f"Selected text:\n{selected_text}"))
            
            # Async invoke the model
            task = asyncio.create_task(chat.ainvoke(messages))
            
            # Set task completion callback to ensure task is properly cleaned up
            def done_callback(t):
                try:
                    # Check if task has an exception
                    if t.exception() is not None and not isinstance(t.exception(), asyncio.CancelledError):
                        logger.error(f"Task completed with exception: {t.exception()}", exc_info=True)
                except asyncio.CancelledError:
                    logger.warning("Task was cancelled")
                except Exception as e:
                    logger.error(f"Error in done callback: {e}", exc_info=True)
                    
            task.add_done_callback(done_callback)
            
            # Collect full response and send insert action
            full_response = ""
            
            # Process streaming output
            try:
                while not task.done() or not token_queue.empty():
                    try:
                        # Get token from queue in non-blocking way
                        token = await asyncio.wait_for(token_queue.get(), timeout=0.1)
                        full_response += token
                    except asyncio.TimeoutError:
                        # No token available, just continue
                        pass
                    except Exception as e:
                        # Log error and continue
                        logger.error(f"Error processing token: {e}", exc_info=True)
            except asyncio.CancelledError:
                logger.warning("Stream processing was cancelled")
                # Ensure task is cancelled
                if not task.done():
                    task.cancel()
                raise  # Re-raise exception to let caller know processing was cancelled
            except Exception as e:
                logger.error(f"Error in stream processing loop: {e}", exc_info=True)
                # Ensure task is cancelled
                if not task.done():
                    task.cancel()
            
            # Wait for model task to complete
            try:
                await task
            except asyncio.CancelledError:
                logger.warning("Task await was cancelled")
                raise  # Re-raise exception
            except Exception as e:
                logger.error(f"Error awaiting task: {e}", exc_info=True)
            
            # Extract the actual content from LLM response
            # We need to filter out the analysis/thinking process and only keep the actual content
            extracted_content = extract_actual_content(full_response.strip())
            
            # Build simple insert action
            action = build_simple_insert_action(extracted_content)
            
            # Send action message
            yield {"type": "action", "content": "Content ready to be inserted into the editor.", "action": action}
            return
            
        # 处理其他类型（other）：插入到编辑器，不在聊天窗口流式显示
        if top_intent.intent_type == "other":
            # 发送思考消息
            yield {"type": "thinking", "content": "Generating content to insert into editor..."}
            
            # 创建异步队列用于实时处理token
            token_queue = asyncio.Queue()
            
            # 创建流式回调处理器
            handler = StreamingCallbackHandler(token_queue)
            
            # 创建聊天模型
            chat = create_langchain_chat_model(model, temperature, handler)
            
            # 构造消息
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
                
            # 如果有选中文本，添加到消息中
            if selected_text:
                messages.append(HumanMessage(content=f"Selected text:\n{selected_text}"))
            
            # 异步调用模型
            task = asyncio.create_task(chat.ainvoke(messages))
            
            # 设置任务完成回调，确保任务被正确清理
            def done_callback(t):
                try:
                    # 检查任务是否有异常
                    if t.exception() is not None and not isinstance(t.exception(), asyncio.CancelledError):
                        logger.error(f"Task completed with exception: {t.exception()}", exc_info=True)
                except asyncio.CancelledError:
                    logger.warning("Task was cancelled")
                except Exception as e:
                    logger.error(f"Error in done callback: {e}", exc_info=True)
                    
            task.add_done_callback(done_callback)
            
            # 收集完整响应，不进行流式显示
            full_response = ""
            
            # 处理流式输出
            try:
                while not task.done() or not token_queue.empty():
                    try:
                        # 以非阻塞方式从队列获取token
                        token = await asyncio.wait_for(token_queue.get(), timeout=0.1)
                        full_response += token
                    except asyncio.TimeoutError:
                        # 没有可用的token，继续
                        pass
                    except Exception as e:
                        # 记录错误并继续
                        logger.error(f"Error processing token: {e}", exc_info=True)
            except asyncio.CancelledError:
                logger.warning("Stream processing was cancelled")
                # 确保任务被取消
                if not task.done():
                    task.cancel()
                raise  # 重新抛出异常，让调用者知道处理被取消
            except Exception as e:
                logger.error(f"Error in stream processing loop: {e}", exc_info=True)
                # 确保任务被取消
                if not task.done():
                    task.cancel()
            
            # 等待模型任务完成
            try:
                await task
            except asyncio.CancelledError:
                logger.warning("Task await was cancelled")
                raise  # 重新抛出异常
            except Exception as e:
                logger.error(f"Error awaiting task: {e}", exc_info=True)
            
            # 构建简单插入动作
            action = build_simple_insert_action(full_response.strip())
            
            # 发送动作消息
            yield {"type": "action", "content": "Content ready to be inserted into the editor.", "action": action}
            return
            
        use_thinking_pipeline = (
            top_intent.intent_type == "modify_existing"
            and top_intent.confidence > 0.6
            and editor_content
            and editor_content.strip()
        )
        
        if use_thinking_pipeline:
            # 使用新的thinking流水线处理用户输入，并在出错时回退
            yield msg
        if handled:
            return
        
        # Create async queue for real-time token processing
        token_queue = asyncio.Queue()
        
        # Send "thinking" message
        yield {"type": "thinking", "content": "Analyzing your request..."}
        
        # Create streaming callback handler
        handler = StreamingCallbackHandler(token_queue)
        
        # Create chat model
        chat = create_langchain_chat_model(model, temperature, handler)
        
        # Construct messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
                    
        # If there is selected text, add it to the messages
        if selected_text:
            messages.append(HumanMessage(content=f"Selected text:\n{selected_text}"))
        
        # Async invoke the model
        task = asyncio.create_task(chat.ainvoke(messages))
        
        # Variables for collecting thinking process
        current_thinking = ""
        thinking_buffer = ""
        action_pattern = re.compile(r'\[ACTION\](.*?)\[/ACTION\]', re.DOTALL)
        
        # Process streaming output
        while not task.done() or not token_queue.empty():
            try:
                # Get token from queue in non-blocking way
                token = await asyncio.wait_for(token_queue.get(), timeout=0.1)
                thinking_buffer += token
                
                # Check if there is a complete thinking step
                if token in ['.', '?', '!', '\n'] and len(thinking_buffer.strip()) > 0:
                    # Check if there is a complete or partial ACTION block
                    # Remove complete ACTION block
                    clean_thinking = re.sub(r'\[ACTION\].*?\[/ACTION\]', '', thinking_buffer, flags=re.DOTALL)
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
