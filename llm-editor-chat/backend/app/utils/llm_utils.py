"""
LLM 工具函数模块

提供通用的LLM调用辅助函数，简化与OpenAI API的交互。
"""
import logging
from typing import List, Dict, AsyncGenerator, Union, Optional, Any

from app.features.llm.services.factory import LLMServiceFactory
from app.features.llm.services.base import LLMResponse

logger = logging.getLogger(__name__)

async def generate_text(
    prompt: str,
    system_message: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    temperature: float = 0.7,
    streaming: bool = True,
    chat_history: Optional[List[Dict[str, str]]] = [],
    **kwargs
) -> str:
    """
    Generate text using the LLM service
    
    Args:
        prompt: User prompt/用户提示
        system_message: System message/系统消息
        model: Model name, using default if None/模型名称，如果为None则使用默认模型
        temperature: Temperature parameter/温度参数
        streaming: Whether to use streaming generation, defaults to True/是否使用流式生成，默认为True
        chat_history: Chat history, will be limited to 5 most recent entries/聊天历史，将限制为最近5条
        **kwargs: Additional parameters to pass to the LLM/其他传递给LLM的参数
        
    Returns:
        Generated complete text/生成的完整文本
    """
    llm_service = LLMServiceFactory.get_instance()
    # Start with system message
    messages = [{"role": "system", "content": system_message}]
    
    # Add chat history if available, limited to the 5 most recent entries, and not skipped
    if chat_history and len(chat_history) > 0:
        # Read top intent and conversation history relevance from context variables
        skip_history = False
        try:
            from app.features.chat.router import get_current_intent
            top_intent = get_current_intent()
            if top_intent and hasattr(top_intent, 'additional_info') and top_intent.additional_info:
                if top_intent.additional_info.get('conversation_history_relevance') == 'independent':
                    skip_history = True
        except (ImportError, AttributeError) as e:
            # If there's any error accessing the intent, proceed with chat history
            pass
        
        if not skip_history:
            # Limit chat history to the 5 most recent entries
            limited_history = chat_history[-5:] if len(chat_history) > 5 else chat_history
            
            # Find the last user message index (if any)
            last_user_index = None
            for i in range(len(limited_history) - 1, -1, -1):
                if limited_history[i].get('sender') == 'user':
                    last_user_index = i
                    break

            # Add all messages except the last user message
            for i, msg in enumerate(limited_history):
                # Skip the last user message as we'll add the current prompt at the end
                if i == last_user_index:
                    continue

                if msg.get('sender') and msg.get('content') and msg['content']:
                    role = "assistant" if msg['sender'] == "assistant" else "user"
                    messages.append({"role": role, "content": msg['content']})
    
    # Add current user message
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = []
        async for chunk in llm_service.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            streaming=streaming,
            **kwargs
        ):
            if isinstance(chunk, str):
                response.append(chunk)
            elif isinstance(chunk, LLMResponse):
                # 当streaming=False时，我们会直接收到一个LLMResponse对象
                # 需要将其内容添加到响应中
                if not streaming and hasattr(chunk, 'content'):
                    response.append(chunk.content)
                # 当streaming=True时，忽略最终的LLMResponse，因为它的内容已经在之前的chunks中
            else:
                response.append(chunk.content)
        
        return "".join(response)
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}", exc_info=True)
        raise

async def stream_text(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    streaming: bool = True,
    **kwargs
) -> AsyncGenerator[str, None]:
    """
    流式生成文本的辅助函数
    
    Args:
        messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
        model: 模型名称，如果为None则使用默认模型
        temperature: 温度参数
        streaming: 是否使用流式生成，默认为True
        **kwargs: 其他传递给LLM的参数
        
    Yields:
        生成的文本块
    """
    llm_service = LLMServiceFactory.get_instance()
    
    try:
        # 跟踪已生成的内容，用于检测重复
        generated_content = set()
        
        async for chunk in llm_service.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            streaming=streaming,
            **kwargs
        ):
            if isinstance(chunk, str):
                # 字符串块直接传递
                yield chunk
                generated_content.add(chunk)
            elif isinstance(chunk, LLMResponse):
                # 当streaming=False时，我们会直接收到一个LLMResponse对象
                # 需要将其内容传递出去
                if not streaming and hasattr(chunk, 'content'):
                    yield chunk.content
                    generated_content.add(chunk.content)
                # 当streaming=True时，忽略LLMResponse
            else:
                # 其他类型尝试转换为字符串
                yield str(chunk)
                generated_content.add(str(chunk))
    except Exception as e:
        logger.error(f"Error streaming text: {str(e)}", exc_info=True)
        raise

async def generate_with_history(
    user_message: str,
    conversation_history: List[Dict[str, str]] = None,
    system_message: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    temperature: float = 0.7,
    streaming: bool = True,
    **kwargs
) -> str:
    """
    考虑对话历史的文本生成函数
    
    Args:
        user_message: 用户当前消息
        conversation_history: 对话历史记录，格式为 [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        system_message: 系统消息
        model: 模型名称，如果为None则使用默认模型
        temperature: 温度参数
        streaming: 是否使用流式生成，默认为True
        **kwargs: 其他传递给LLM的参数
        
    Returns:
        生成的完整文本
    """
    messages = []
    
    # 添加系统消息
    messages.append({"role": "system", "content": system_message})
    
    # 添加对话历史
    if conversation_history:
        messages.extend(conversation_history)
    
    # 添加用户当前消息
    messages.append({"role": "user", "content": user_message})
    
    # 获取LLM服务实例并直接调用，而不是通过generate_text
    llm_service = LLMServiceFactory.get_instance()
    
    try:
        response = []
        async for chunk in llm_service.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            streaming=streaming,
            **kwargs
        ):
            if isinstance(chunk, str):
                response.append(chunk)
            elif isinstance(chunk, LLMResponse):
                # 当streaming=False时，我们会直接收到一个LLMResponse对象
                # 需要将其内容添加到响应中
                if not streaming and hasattr(chunk, 'content'):
                    response.append(chunk.content)
                # 当streaming=True时，忽略最终的LLMResponse
            else:
                response.append(chunk.content)
        
        return "".join(response)
    except Exception as e:
        logger.error(f"Error generating text with history: {str(e)}", exc_info=True)
        raise
