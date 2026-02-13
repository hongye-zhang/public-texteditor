from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import re

router = APIRouter(prefix="/command", tags=["command-parsing"])

class CommandRequest(BaseModel):
    """命令解析请求模型"""
    command: str
    document_content: Optional[str] = None
    selected_text: Optional[str] = None
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None

class CommandAction(BaseModel):
    """命令动作模型"""
    action_type: str  # select, modify, format, navigate, create, etc.
    parameters: Dict[str, Any]

class CommandResponse(BaseModel):
    """命令解析响应模型"""
    success: bool
    message: str
    action: Optional[CommandAction] = None
    requires_confirmation: bool = False

@router.post("/parse", response_model=CommandResponse)
async def parse_command(request: CommandRequest):
    """解析自然语言命令"""
    try:
        command = request.command.lower()
        
        # 文本选择命令
        if re.search(r"选择|选中|找到", command):
            return handle_selection_command(command, request)
        
        # 文本修改命令
        elif re.search(r"修改|替换|改为|更改", command):
            return handle_modification_command(command, request)
        
        # 格式化命令
        elif re.search(r"加粗|斜体|标题|引用|列表", command):
            return handle_formatting_command(command, request)
        
        # PPT/文档结构命令
        elif re.search(r"创建幻灯片|添加页面|新建页|生成ppt|制作ppt", command):
            return handle_document_command(command, request)
        
        # 如果无法识别命令
        return CommandResponse(
            success=False,
            message="无法识别的命令，请尝试使用更明确的指令",
            requires_confirmation=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析命令时出错: {str(e)}")

def handle_selection_command(command: str, request: CommandRequest) -> CommandResponse:
    """处理文本选择命令"""
    # 选择第一段
    if re.search(r"选择第一段|选中第一段", command):
        return CommandResponse(
            success=True,
            message="已解析选择第一段的命令",
            action=CommandAction(
                action_type="select",
                parameters={"target": "first_paragraph"}
            ),
            requires_confirmation=False
        )
    
    # 选择标题
    elif re.search(r"选择标题|选中标题", command):
        return CommandResponse(
            success=True,
            message="已解析选择标题的命令",
            action=CommandAction(
                action_type="select",
                parameters={"target": "heading"}
            ),
            requires_confirmation=False
        )
    
    # 选择特定文本
    elif "选择" in command and "文本" in command:
        # 尝试提取要选择的文本
        match = re.search(r"选择[\"\'](.*?)[\"\']", command)
        if match:
            text_to_select = match.group(1)
            return CommandResponse(
                success=True,
                message=f"已解析选择特定文本的命令",
                action=CommandAction(
                    action_type="select",
                    parameters={"target": "text", "text": text_to_select}
                ),
                requires_confirmation=False
            )
    
    # 如果无法识别具体的选择命令
    return CommandResponse(
        success=False,
        message="无法识别的选择命令，请尝试更明确的指令，例如'选择第一段'或'选择标题'",
        requires_confirmation=False
    )

def handle_modification_command(command: str, request: CommandRequest) -> CommandResponse:
    """处理文本修改命令"""
    # 检查是否有选中的文本
    if not request.selected_text:
        return CommandResponse(
            success=False,
            message="请先选择要修改的文本",
            requires_confirmation=False
        )
    
    # 替换文本
    if "替换为" in command:
        # 尝试提取新文本
        match = re.search(r"替换为[\"\'](.*?)[\"\']", command)
        if match:
            new_text = match.group(1)
            return CommandResponse(
                success=True,
                message=f"已解析替换文本的命令",
                action=CommandAction(
                    action_type="modify",
                    parameters={
                        "operation": "replace",
                        "new_text": new_text,
                        "start": request.selection_start,
                        "end": request.selection_end
                    }
                ),
                requires_confirmation=True
            )
    
    # 如果无法识别具体的修改命令
    return CommandResponse(
        success=False,
        message="无法识别的修改命令，请尝试更明确的指令，例如'替换为\"新文本\"'",
        requires_confirmation=False
    )

def handle_formatting_command(command: str, request: CommandRequest) -> CommandResponse:
    """处理格式化命令"""
    # 检查是否有选中的文本
    if not request.selected_text:
        return CommandResponse(
            success=False,
            message="请先选择要格式化的文本",
            requires_confirmation=False
        )
    
    # 加粗文本
    if "加粗" in command:
        return CommandResponse(
            success=True,
            message="已解析加粗文本的命令",
            action=CommandAction(
                action_type="format",
                parameters={
                    "format_type": "bold",
                    "start": request.selection_start,
                    "end": request.selection_end
                }
            ),
            requires_confirmation=False
        )
    
    # 设置为标题
    elif "标题" in command:
        level = 1  # 默认为一级标题
        if "二级" in command or "2级" in command:
            level = 2
        elif "三级" in command or "3级" in command:
            level = 3
            
        return CommandResponse(
            success=True,
            message=f"已解析设置为{level}级标题的命令",
            action=CommandAction(
                action_type="format",
                parameters={
                    "format_type": f"heading{level}",
                    "start": request.selection_start,
                    "end": request.selection_end
                }
            ),
            requires_confirmation=False
        )
    
    # 如果无法识别具体的格式化命令
    return CommandResponse(
        success=False,
        message="无法识别的格式化命令，请尝试更明确的指令，例如'加粗'或'设为二级标题'",
        requires_confirmation=False
    )

def handle_document_command(command: str, request: CommandRequest) -> CommandResponse:
    """处理文档/PPT结构命令"""
    # 创建PPT
    if re.search(r"创建|生成|制作", command) and re.search(r"ppt|幻灯片|演示文稿", command):
        # 尝试提取主题
        topic = "未指定主题"
        match = re.search(r"关于[\"\'](.*?)[\"\']的", command)
        if match:
            topic = match.group(1)
        else:
            # 尝试其他模式
            match = re.search(r"主题是[\"\'](.*?)[\"\']", command)
            if match:
                topic = match.group(1)
        
        # 尝试提取幻灯片数量
        slide_count = 10  # 默认10页
        match = re.search(r"(\d+)页|(\d+)张", command)
        if match:
            count = match.group(1) or match.group(2)
            if count:
                slide_count = int(count)
        
        return CommandResponse(
            success=True,
            message=f"已解析创建PPT的命令，主题：{topic}，页数：{slide_count}",
            action=CommandAction(
                action_type="create_document",
                parameters={
                    "document_type": "presentation",
                    "topic": topic,
                    "slide_count": slide_count
                }
            ),
            requires_confirmation=True
        )
    
    # 添加幻灯片
    elif re.search(r"添加|新建", command) and re.search(r"页面|幻灯片|页", command):
        # 尝试提取标题
        title = "新页面"
        match = re.search(r"标题是[\"\'](.*?)[\"\']", command)
        if match:
            title = match.group(1)
        
        return CommandResponse(
            success=True,
            message=f"已解析添加页面的命令，标题：{title}",
            action=CommandAction(
                action_type="add_slide",
                parameters={
                    "title": title,
                    "content": ""  # 内容可以后续添加
                }
            ),
            requires_confirmation=False
        )
    
    # 如果无法识别具体的文档命令
    return CommandResponse(
        success=False,
        message="无法识别的文档命令，请尝试更明确的指令，例如'创建关于\"AI\"的PPT'或'添加标题是\"方法\"的页面'",
        requires_confirmation=False
    )
