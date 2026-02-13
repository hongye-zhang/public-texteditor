from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio
import re

# 导入共享服务模块
from app.services.llm_service import stream_llm_response

router = APIRouter(prefix="/text", tags=["text-modification"])

class ModificationRequest(BaseModel):
    """文本修改请求模型"""
    document_id: Optional[str] = None
    start_position: int
    end_position: int
    new_content: str
    original_content: Optional[str] = None  # 用于验证

class StreamModificationRequest(BaseModel):
    """流式文本修改请求模型"""
    message: str  # 用户的修改指令
    selected_text: str  # 选中的文本
    start_position: int  # 选中文本的起始位置
    end_position: int  # 选中文本的结束位置
    editor_content: Optional[str] = None  # 编辑器的完整内容（可选）

class ModificationResponse(BaseModel):
    """文本修改响应模型"""
    success: bool
    message: str
    modified_content: Optional[str] = None
    start_position: int
    end_position: int

@router.post("/modify", response_model=ModificationResponse)
async def modify_text(request: ModificationRequest):
    """修改选定的文本"""
    try:
        # 这里将来会调用服务层函数
        # 目前返回模拟数据
        return ModificationResponse(
            success=True,
            message="文本已成功修改",
            modified_content=request.new_content,
            start_position=request.start_position,
            end_position=request.start_position + len(request.new_content)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"修改文本时出错: {str(e)}")

@router.post("/stream-modify")
async def stream_modify_text(request: StreamModificationRequest):
    """流式修改选定的文本，提供思考过程"""
    
    
    async def generate():
        try:
            # 系统提示词
            system_prompt = """You are a text modification assistant. When a user asks you to modify selected text, you need to:
1. Analyze the user's request and explain your thinking process
2. Generate the modified content that meets the user's requirements
3. Finally, provide a clear action instruction to replace the selected text

When you need to replace content in the editor, use the following format:

[ACTION]
{
  "type": "replace",
  "payload": {
    "content": "modified content",
    "start": start_position,
    "end": end_position
  }
}
[/ACTION]
"""
            
            # 使用共享服务模块处理LLM流式响应
            async for event in stream_llm_response(
                system_prompt=system_prompt,
                user_message=request.message,
                editor_content=request.editor_content,
                selected_text=request.selected_text
            ):
                # 如果是动作事件，修改动作类型和添加位置信息
                if event.get("type") == "action" and event.get("action"):
                    action = event["action"]
                    
                    # 检查内容中是否包含ACTION块
                    content = action.get("payload", {}).get("content", "")
                    action_pattern = re.compile(r'\[ACTION\](.*?)\[/ACTION\]', re.DOTALL)
                    action_match = action_pattern.search(content)
                    
                    if action_match:
                        # 如果内容中包含ACTION块，尝试提取真正的替换内容
                        try:
                            # 提取ACTION块中的JSON
                            action_json = action_match.group(1).strip()
                            nested_action = json.loads(action_json)
                            
                            
                            # 使用嵌套action中的content
                            if nested_action.get("type") == "replace" and "payload" in nested_action and "content" in nested_action["payload"]:
                                action["payload"]["content"] = nested_action["payload"]["content"]

                        except json.JSONDecodeError as e:
                            pass
                    
                    # 确保动作类型为replace
                    if action.get("type") != "replace":
                        action["type"] = "replace"
                    
                    # 无论动作类型是什么，都使用前端传递的位置信息
                    if "payload" in action:
                        # 使用前端传递的位置信息
                        action["payload"]["start"] = request.start_position
                        action["payload"]["end"] = request.end_position
                
                # 将事件格式化为SSE格式
                yield f"data: {json.dumps(event)}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error occurred: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

class FormatRequest(BaseModel):
    """文本格式化请求模型"""
    document_id: Optional[str] = None
    start_position: int
    end_position: int
    format_type: str  # 如 "bold", "italic", "heading1" 等
    original_content: Optional[str] = None

@router.post("/format", response_model=ModificationResponse)
async def format_text(request: FormatRequest):
    """格式化选定的文本"""
    try:
        # 这里将来会调用服务层函数
        # 目前返回模拟数据
        format_mapping = {
            "bold": lambda text: f"**{text}**",
            "italic": lambda text: f"*{text}*",
            "heading1": lambda text: f"# {text}",
            "heading2": lambda text: f"## {text}",
            "heading3": lambda text: f"### {text}",
            "code": lambda text: f"`{text}`",
            "blockquote": lambda text: f"> {text}",
        }
        
        # 假设我们有原始内容
        original_content = request.original_content or "示例文本"
        
        if request.format_type in format_mapping:
            formatted_text = format_mapping[request.format_type](original_content)
            return ModificationResponse(
                success=True,
                message=f"文本已成功格式化为{request.format_type}",
                modified_content=formatted_text,
                start_position=request.start_position,
                end_position=request.start_position + len(formatted_text)
            )
        else:
            raise HTTPException(status_code=400, detail=f"不支持的格式类型: {request.format_type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"格式化文本时出错: {str(e)}")

class CommandModificationRequest(BaseModel):
    """通过命令修改文本的请求模型"""
    command: str
    document_content: str
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    selected_text: Optional[str] = None

@router.post("/modify-by-command", response_model=ModificationResponse)
async def modify_by_command(request: CommandModificationRequest):
    """解析自然语言命令来修改文本"""
    try:
        # 这里将来会使用NLP来理解命令
        # 目前返回模拟数据
        command = request.command.lower()
        
        # 简单的命令解析逻辑
        if "加粗" in command and request.selected_text:
            modified_text = f"**{request.selected_text}**"
            return ModificationResponse(
                success=True,
                message="已将文本加粗",
                modified_content=modified_text,
                start_position=request.start_position or 0,
                end_position=(request.start_position or 0) + len(modified_text)
            )
        elif "改为标题" in command and request.selected_text:
            heading_level = 1
            if "二级" in command:
                heading_level = 2
            elif "三级" in command:
                heading_level = 3
                
            prefix = "#" * heading_level + " "
            modified_text = f"{prefix}{request.selected_text}"
            
            return ModificationResponse(
                success=True,
                message=f"已将文本改为{heading_level}级标题",
                modified_content=modified_text,
                start_position=request.start_position or 0,
                end_position=(request.start_position or 0) + len(modified_text)
            )
        elif "替换" in command and request.selected_text:
            # 简单的替换逻辑，实际实现会更复杂
            # 假设命令格式为"将X替换为Y"
            parts = command.split("替换为")
            if len(parts) == 2:
                new_text = parts[1].strip()
                return ModificationResponse(
                    success=True,
                    message=f"已将文本替换为: {new_text}",
                    modified_content=new_text,
                    start_position=request.start_position or 0,
                    end_position=(request.start_position or 0) + len(new_text)
                )
        
        # 如果找不到匹配的命令
        raise HTTPException(status_code=400, detail="无法理解命令或无法执行修改操作")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理命令时出错: {str(e)}")
