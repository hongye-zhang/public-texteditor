from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/text", tags=["text-selection"])

class SelectionRequest(BaseModel):
    """requesting model for text selection"""
    document_id: Optional[str] = None
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    search_text: Optional[str] = None
    context: Optional[str] = None

class SelectionResponse(BaseModel):
    """reaction model for text selection"""
    selected_text: str
    start_position: int
    end_position: int
    success: bool
    message: str

@router.post("/select", response_model=SelectionResponse)
async def select_text(request: SelectionRequest):
    """selects text from document according to location or content """
    try:
        # 这里将来会调用服务层函数
        # 目前返回模拟数据
        if request.search_text:
            # 基于搜索文本选择
            return SelectionResponse(
                selected_text=request.search_text,
                start_position=0,  # 这将由实际实现确定
                end_position=len(request.search_text),  # 这将由实际实现确定
                success=True,
                message="text has been successfully selected"
            )
        elif request.start_position is not None and request.end_position is not None:
            # 基于位置选择
            # 这里需要从文档中获取实际文本
            # 目前返回模拟数据
            return SelectionResponse(
                selected_text="selected text content",
                start_position=request.start_position,
                end_position=request.end_position,
                success=True,
                message="text selected successfully"
            )
        else:
            raise HTTPException(status_code=400, detail="must provide either search_text or start_position and end_position")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"error selecting text: {str(e)}")

class CommandSelectionRequest(BaseModel):
    """requesting model for text selection by command"""
    command: str
    document_content: str

@router.post("/select-by-command", response_model=SelectionResponse)
async def select_by_command(request: CommandSelectionRequest):
    """analyses natural language command to select text from document"""
    try:
        # 这里将来会使用NLP来理解命令
        # 目前返回模拟数据
        command = request.command.lower()
        content = request.document_content
        
        # 简单的命令解析逻辑
        if "选择第一段" in command:
            # 查找第一段落
            paragraphs = content.split("\n\n")
            if paragraphs:
                first_para = paragraphs[0]
                start_pos = content.find(first_para)
                end_pos = start_pos + len(first_para)
                
                return SelectionResponse(
                    selected_text=first_para,
                    start_position=start_pos,
                    end_position=end_pos,
                    success=True,
                    message="已选择第一段"
                )
        elif "选择标题" in command:
            # 查找标题（假设标题以#开头）
            lines = content.split("\n")
            for line in lines:
                if line.strip().startswith("#"):
                    start_pos = content.find(line)
                    end_pos = start_pos + len(line)
                    return SelectionResponse(
                        selected_text=line,
                        start_position=start_pos,
                        end_position=end_pos,
                        success=True,
                        message="已选择标题"
                    )
        
        # 如果找不到匹配的命令
        raise HTTPException(status_code=400, detail="无法理解命令或找不到匹配的文本")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理命令时出错: {str(e)}")
