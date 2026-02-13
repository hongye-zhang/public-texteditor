from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/document", tags=["document-structure"])

class Slide(BaseModel):
    """PPT幻灯片模型"""
    id: str
    title: str
    content: str
    order: int
    type: str = "standard"  # standard, title, section, etc.

class DocumentRequest(BaseModel):
    """文档创建请求模型"""
    title: str
    template_type: Optional[str] = "standard"  # standard, presentation, report, etc.
    initial_content: Optional[str] = None

class DocumentResponse(BaseModel):
    """文档响应模型"""
    document_id: str
    title: str
    success: bool
    message: str

class SlideRequest(BaseModel):
    """幻灯片请求模型"""
    document_id: str
    title: str
    content: str
    slide_type: Optional[str] = "standard"
    position: Optional[int] = None  # 如果不提供，则添加到末尾

class SlideResponse(BaseModel):
    """幻灯片响应模型"""
    slide_id: str
    document_id: str
    title: str
    success: bool
    message: str

class OutlineItem(BaseModel):
    """大纲项目模型"""
    id: str
    title: str
    level: int
    parent_id: Optional[str] = None
    children: List["OutlineItem"] = []

class DocumentOutline(BaseModel):
    """文档大纲模型"""
    document_id: str
    title: str
    items: List[OutlineItem]

@router.post("/create", response_model=DocumentResponse)
async def create_document(request: DocumentRequest):
    """创建新文档"""
    try:
        # 这里将来会调用服务层函数
        # 目前返回模拟数据
        return DocumentResponse(
            document_id="doc_" + request.title.lower().replace(" ", "_"),
            title=request.title,
            success=True,
            message="文档已成功创建"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建文档时出错: {str(e)}")

@router.post("/slides/add", response_model=SlideResponse)
async def add_slide(request: SlideRequest):
    """添加新幻灯片"""
    try:
        # 这里将来会调用服务层函数
        # 目前返回模拟数据
        return SlideResponse(
            slide_id=f"slide_{request.document_id}_{request.title.lower().replace(' ', '_')}",
            document_id=request.document_id,
            title=request.title,
            success=True,
            message="幻灯片已成功添加"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加幻灯片时出错: {str(e)}")

@router.get("/slides/{document_id}", response_model=List[Slide])
async def get_slides(document_id: str):
    """获取文档的所有幻灯片"""
    try:
        # 这里将来会调用服务层函数
        # 目前返回模拟数据
        return [
            Slide(
                id=f"slide_{document_id}_1",
                title="标题页",
                content="# 演示文稿标题\n## 副标题",
                order=1,
                type="title"
            ),
            Slide(
                id=f"slide_{document_id}_2",
                title="内容概述",
                content="## 内容概述\n- 第一部分\n- 第二部分\n- 第三部分",
                order=2,
                type="standard"
            ),
            Slide(
                id=f"slide_{document_id}_3",
                title="第一部分",
                content="## 第一部分\n这里是第一部分的详细内容...",
                order=3,
                type="standard"
            )
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取幻灯片时出错: {str(e)}")

@router.get("/outline/{document_id}", response_model=DocumentOutline)
async def get_document_outline(document_id: str):
    """获取文档大纲"""
    try:
        # 这里将来会调用服务层函数
        # 目前返回模拟数据
        return DocumentOutline(
            document_id=document_id,
            title="示例演示文稿",
            items=[
                OutlineItem(
                    id="item_1",
                    title="引言",
                    level=1,
                    children=[
                        OutlineItem(
                            id="item_1_1",
                            title="背景",
                            level=2,
                            parent_id="item_1"
                        ),
                        OutlineItem(
                            id="item_1_2",
                            title="研究目标",
                            level=2,
                            parent_id="item_1"
                        )
                    ]
                ),
                OutlineItem(
                    id="item_2",
                    title="方法",
                    level=1,
                    children=[
                        OutlineItem(
                            id="item_2_1",
                            title="数据收集",
                            level=2,
                            parent_id="item_2"
                        ),
                        OutlineItem(
                            id="item_2_2",
                            title="分析方法",
                            level=2,
                            parent_id="item_2"
                        )
                    ]
                ),
                OutlineItem(
                    id="item_3",
                    title="结论",
                    level=1
                )
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档大纲时出错: {str(e)}")

class PptGenerationRequest(BaseModel):
    """PPT生成请求模型"""
    topic: str
    slide_count: Optional[int] = 10
    style: Optional[str] = "professional"  # professional, creative, minimal, etc.
    outline: Optional[List[str]] = None

@router.post("/generate-ppt", response_model=DocumentResponse)
async def generate_ppt(request: PptGenerationRequest):
    """生成完整的PPT文档"""
    try:
        # 这里将来会调用LLM服务生成PPT内容
        # 目前返回模拟数据
        return DocumentResponse(
            document_id=f"ppt_{request.topic.lower().replace(' ', '_')}",
            title=request.topic,
            success=True,
            message=f"已成功生成关于'{request.topic}'的PPT，包含{request.slide_count}张幻灯片"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成PPT时出错: {str(e)}")
