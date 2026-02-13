from typing import List, Dict, Any, Callable, Optional, AsyncGenerator
import asyncio
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)
api_key = os.getenv("OPENAI_API_KEY")
if api_key is None:
    raise ValueError("OPENAI_API_KEY environment variable not found")

class StreamingCallbackHandler(StreamingStdOutCallbackHandler):
    """自定义流式回调处理器"""
    def __init__(self, queue):
        super().__init__()
        self.tokens = []
        self.queue = queue
        
    def on_llm_new_token(self, token: str, **kwargs):
        self.tokens.append(token)
        # 将新token放入队列进行实时处理
        self.queue.put_nowait(token)
        
    def get_tokens(self):
        return self.tokens

async def stream_llm_response(
    system_prompt: str,
    user_message: str,
    editor_content: Optional[str] = None,
    selected_text: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 0.7
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
        # 创建异步队列用于实时token处理
        token_queue = asyncio.Queue()
        
        # 发送"思考中"消息
        yield {"type": "thinking", "content": "Analyzing your request..."}
        
        # 创建流式回调处理器
        handler = StreamingCallbackHandler(token_queue)
        
        # 创建聊天模型
        chat = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=temperature,
            streaming=True,
            callbacks=[handler],
            verbose=True
        )
        
        # 构建消息
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        # 如果有编辑器内容，添加到消息中
        if editor_content:
            messages.append(HumanMessage(content=f"Current editor content:\n{editor_content}"))
            
        # 如果有选中文本，添加到消息中
        if selected_text:
            messages.append(HumanMessage(content=f"Selected text:\n{selected_text}"))
        
        # 异步调用模型
        task = asyncio.create_task(chat.ainvoke(messages))
        
        # 用于收集思考过程的变量
        current_thinking = ""
        thinking_buffer = ""
        action_pattern = re.compile(r'\[ACTION\](.*?)\[/ACTION\]', re.DOTALL)
        
        # 处理流式输出
        while not task.done() or not token_queue.empty():
            try:
                # 非阻塞方式从队列获取token
                token = await asyncio.wait_for(token_queue.get(), timeout=0.1)
                thinking_buffer += token
                
                # 检查是否有完整的思考步骤
                if token in ['.', '?', '!', '\n'] and len(thinking_buffer.strip()) > 0:
                    # 先检查是否包含ACTION块，如果有，在发送思考步骤前移除
                    # 移除完整的ACTION块
                    clean_thinking = re.sub(r'\[ACTION\].*?\[/ACTION\]', '', thinking_buffer, flags=re.DOTALL)
                    # 移除不完整的ACTION块（只有开始标记）
                    clean_thinking = re.sub(r'\[ACTION\].*', '', clean_thinking, flags=re.DOTALL)
                    # 移除不完整的ACTION块（只有结束标记）
                    clean_thinking = re.sub(r'.*\[/ACTION\]', '', clean_thinking, flags=re.DOTALL)
                    # 移除可能的JSON片段（多个连续的花括号或大括号）
                    clean_thinking = re.sub(r'[\}\]]{2,}\s*$', '', clean_thinking)
                    clean_thinking = clean_thinking.strip()
                    
                    # 如果清理后的思考内容为空，则跳过
                    if not clean_thinking:
                        thinking_buffer = ""
                        continue
                        
                    sentences = re.split(r'(?<=[.!?])\s+', clean_thinking)
                    
                    if len(sentences) > 1:
                        # 将完整的句子作为思考步骤发送
                        for i in range(len(sentences) - 1):
                            if sentences[i].strip():
                                yield {"type": "thinking", "content": sentences[i].strip()}
                        
                        # 保留最后一个可能不完整的句子
                        thinking_buffer = sentences[-1]
                
                # 检查是否有ACTION指令
                action_match = action_pattern.search(thinking_buffer)
                if action_match:
                    # 找到ACTION指令，提取JSON内容
                    action_json = action_match.group(1).strip()
                    try:
                        action_data = json.loads(action_json)
                        # 在发送最后的thinking消息前，清理所有的ACTION块
                        clean_final_thinking = re.sub(r'\[ACTION\].*?\[/ACTION\]', '', thinking_buffer, flags=re.DOTALL)
                        # 移除不完整的ACTION块（只有开始标记）
                        clean_final_thinking = re.sub(r'\[ACTION\].*', '', clean_final_thinking, flags=re.DOTALL)
                        # 移除不完整的ACTION块（只有结束标记）
                        clean_final_thinking = re.sub(r'.*\[/ACTION\]', '', clean_final_thinking, flags=re.DOTALL)
                        # 移除可能的JSON片段（多个连续的花括号或大括号）
                        clean_final_thinking = re.sub(r'[\}\]]{2,}\s*$', '', clean_final_thinking)
                        clean_final_thinking = clean_final_thinking.strip()
                        if clean_final_thinking:
                            # 发送清理后的最后思考内容
                            yield {"type": "thinking", "content": clean_final_thinking}
                            
                        # 发送准备插入的消息
                        yield {"type": "thinking", "content": "Content generation completed, preparing to insert into editor..."}
                        
                        # 发送动作指令
                        yield {"type": "action", "content": "Content has been generated and inserted into the editor.", "action": action_data}
                        
                        # 结束处理
                        break
                    except json.JSONDecodeError:
                        # JSON解析错误，继续收集更多数据
                        pass
                    
            except asyncio.TimeoutError:
                # 超时，检查是否有内容要发送
                if thinking_buffer.strip() and thinking_buffer != current_thinking:
                    # 检查是否包含完整或部分的ACTION块
                    # 移除完整的ACTION块
                    clean_thinking = re.sub(r'\[ACTION\].*?\[/ACTION\]', '', thinking_buffer, flags=re.DOTALL)
                    # 移除不完整的ACTION块（只有开始标记）
                    clean_thinking = re.sub(r'\[ACTION\].*', '', clean_thinking, flags=re.DOTALL)
                    # 移除不完整的ACTION块（只有结束标记）
                    clean_thinking = re.sub(r'.*\[/ACTION\]', '', clean_thinking, flags=re.DOTALL)
                    # 移除可能的JSON片段（多个连续的花括号或大括号）
                    clean_thinking = re.sub(r'[\}\]]{2,}\s*$', '', clean_thinking)
                    clean_thinking = clean_thinking.strip()
                    
                    # 如果清理后的思考内容不为空，才发送
                    if clean_thinking:
                        current_thinking = thinking_buffer
                        yield {"type": "thinking", "content": clean_thinking}
                        thinking_buffer = ""
        
        # 如果没有找到ACTION指令，使用完整的响应
        if not action_pattern.search(thinking_buffer):
            # 获取完整响应
            response = await task
            content = response.content
            
            # 检查完整响应中是否包含ACTION块
            action_match = action_pattern.search(content)
            if action_match:
                # 如果完整响应中包含ACTION块，尝试提取真正的插入内容
                try:
                    # 提取ACTION块中的JSON
                    action_json = action_match.group(1).strip()
                    action_data = json.loads(action_json)
                    
                    # 发送准备插入的消息
                    yield {"type": "thinking", "content": "Content generation completed, preparing to insert into editor..."}
                    
                    # 发送动作指令
                    yield {"type": "action", "content": "Content has been generated and inserted into the editor.", "action": action_data}
                except json.JSONDecodeError:
                    # JSON解析错误，使用默认插入方式
                    # 发送准备插入的消息
                    yield {"type": "thinking", "content": "Content generation completed, preparing to insert into editor..."}
                    
                    # 使用实际的GPT响应发送动作指令，但移除ACTION块
                    clean_content = re.sub(r'\[ACTION\].*?\[/ACTION\]', '', content, flags=re.DOTALL).strip()
                    action = {
                        "type": "insert",
                        "payload": {
                            "content": clean_content
                        }
                    }
                    
                    yield {"type": "action", "content": "Content has been generated and inserted into the editor.", "action": action}
            else:
                # 如果没有ACTION块，直接使用完整响应
                # 发送准备插入的消息
                yield {"type": "thinking", "content": "Content generation completed, preparing to insert into editor..."}
                
                # 使用实际的GPT响应发送动作指令
                action = {
                    "type": "insert",
                    "payload": {
                        "content": content
                    }
                }
                
                yield {"type": "action", "content": "Content has been generated and inserted into the editor.", "action": action}
        
    except Exception as e:
        yield {"type": "error", "content": f"Error occurred: {str(e)}"}
