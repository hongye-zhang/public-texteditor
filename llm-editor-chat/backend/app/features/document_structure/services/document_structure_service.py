from typing import Optional, Dict, Any, List, Tuple
import uuid

class Slide:
    """幻灯片模型"""
    def __init__(self, title: str, content: str, slide_type: str = "standard", order: int = 0):
        self.id = str(uuid.uuid4())
        self.title = title
        self.content = content
        self.type = slide_type
        self.order = order
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "type": self.type,
            "order": self.order
        }

class Document:
    """文档模型"""
    def __init__(self, title: str, template_type: str = "standard"):
        self.id = str(uuid.uuid4())
        self.title = title
        self.template_type = template_type
        self.slides: List[Slide] = []
    
    def add_slide(self, title: str, content: str, slide_type: str = "standard", position: Optional[int] = None) -> Slide:
        """添加幻灯片"""
        if position is None:
            # 添加到末尾
            position = len(self.slides)
        
        # 确保位置有效
        position = max(0, min(position, len(self.slides)))
        
        # 创建新幻灯片
        slide = Slide(title, content, slide_type, position)
        
        # 插入幻灯片
        self.slides.insert(position, slide)
        
        # 更新后续幻灯片的顺序
        for i in range(position + 1, len(self.slides)):
            self.slides[i].order = i
        
        return slide
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "template_type": self.template_type,
            "slides": [slide.to_dict() for slide in self.slides]
        }

class OutlineItem:
    """大纲项目模型"""
    def __init__(self, title: str, level: int, parent_id: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.title = title
        self.level = level
        self.parent_id = parent_id
        self.children: List[OutlineItem] = []
    
    def add_child(self, title: str, level: int) -> 'OutlineItem':
        """添加子项目"""
        child = OutlineItem(title, level, self.id)
        self.children.append(child)
        return child
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "level": self.level,
            "parent_id": self.parent_id,
            "children": [child.to_dict() for child in self.children]
        }

class DocumentStructureService:
    """文档结构服务"""
    
    # 模拟数据存储
    _documents: Dict[str, Document] = {}
    
    @classmethod
    def create_document(cls, title: str, template_type: str = "standard", initial_content: Optional[str] = None) -> Tuple[str, bool, str]:
        """创建新文档
        
        Args:
            title: 文档标题
            template_type: 模板类型
            initial_content: 初始内容
            
        Returns:
            Tuple[str, bool, str]: (文档ID, 是否成功, 消息)
        """
        try:
            document = Document(title, template_type)
            
            # 根据模板类型添加初始幻灯片
            if template_type == "presentation":
                document.add_slide("标题页", f"# {title}\n## 副标题", "title")
                document.add_slide("内容概述", "## 内容概述\n- 第一部分\n- 第二部分\n- 第三部分")
            
            # 如果提供了初始内容，解析并添加幻灯片
            if initial_content:
                cls._parse_content_to_slides(document, initial_content)
            
            # 保存文档
            cls._documents[document.id] = document
            
            return document.id, True, "文档已成功创建"
        except Exception as e:
            return "", False, f"创建文档时出错: {str(e)}"
    
    @classmethod
    def add_slide(cls, document_id: str, title: str, content: str, slide_type: str = "standard", position: Optional[int] = None) -> Tuple[str, bool, str]:
        """添加幻灯片
        
        Args:
            document_id: 文档ID
            title: 幻灯片标题
            content: 幻灯片内容
            slide_type: 幻灯片类型
            position: 插入位置
            
        Returns:
            Tuple[str, bool, str]: (幻灯片ID, 是否成功, 消息)
        """
        try:
            if document_id not in cls._documents:
                return "", False, f"找不到文档: {document_id}"
            
            document = cls._documents[document_id]
            slide = document.add_slide(title, content, slide_type, position)
            
            return slide.id, True, "幻灯片已成功添加"
        except Exception as e:
            return "", False, f"添加幻灯片时出错: {str(e)}"
    
    @classmethod
    def get_slides(cls, document_id: str) -> Tuple[List[Dict[str, Any]], bool, str]:
        """获取文档的所有幻灯片
        
        Args:
            document_id: 文档ID
            
        Returns:
            Tuple[List[Dict[str, Any]], bool, str]: (幻灯片列表, 是否成功, 消息)
        """
        try:
            if document_id not in cls._documents:
                return [], False, f"找不到文档: {document_id}"
            
            document = cls._documents[document_id]
            slides = [slide.to_dict() for slide in document.slides]
            
            return slides, True, "成功获取幻灯片"
        except Exception as e:
            return [], False, f"获取幻灯片时出错: {str(e)}"
    
    @classmethod
    def get_document_outline(cls, document_id: str) -> Tuple[Dict[str, Any], bool, str]:
        """获取文档大纲
        
        Args:
            document_id: 文档ID
            
        Returns:
            Tuple[Dict[str, Any], bool, str]: (大纲数据, 是否成功, 消息)
        """
        try:
            if document_id not in cls._documents:
                return {}, False, f"找不到文档: {document_id}"
            
            document = cls._documents[document_id]
            
            # 从幻灯片生成大纲
            outline_items: List[OutlineItem] = []
            
            for slide in document.slides:
                # 根据幻灯片类型和标题确定级别
                level = 1
                if slide.type == "standard":
                    level = 2
                
                outline_item = OutlineItem(slide.title, level)
                outline_items.append(outline_item)
            
            # 构建大纲结构
            outline = {
                "document_id": document_id,
                "title": document.title,
                "items": [item.to_dict() for item in outline_items]
            }
            
            return outline, True, "成功获取文档大纲"
        except Exception as e:
            return {}, False, f"获取文档大纲时出错: {str(e)}"
    
    @classmethod
    def generate_ppt(cls, topic: str, slide_count: int = 10, style: str = "professional", outline: Optional[List[str]] = None) -> Tuple[str, bool, str]:
        """生成PPT文档
        
        Args:
            topic: 主题
            slide_count: 幻灯片数量
            style: 样式
            outline: 大纲
            
        Returns:
            Tuple[str, bool, str]: (文档ID, 是否成功, 消息)
        """
        try:
            # 创建新文档
            document = Document(topic, "presentation")
            
            # 添加标题幻灯片
            document.add_slide("标题页", f"# {topic}\n## 演示文稿", "title")
            
            # 如果提供了大纲，使用大纲创建幻灯片
            if outline and len(outline) > 0:
                for i, item in enumerate(outline):
                    if i < slide_count - 1:  # 减1是因为已经添加了标题幻灯片
                        document.add_slide(f"第{i+1}页", f"## {item}\n内容待添加...")
            else:
                # 否则创建默认幻灯片
                document.add_slide("内容概述", "## 内容概述\n- 第一部分\n- 第二部分\n- 第三部分")
                
                # 根据请求的幻灯片数量添加更多幻灯片
                for i in range(2, slide_count):
                    document.add_slide(f"第{i}页", f"## 第{i}页标题\n内容待添加...")
            
            # 保存文档
            cls._documents[document.id] = document
            
            return document.id, True, f"已成功生成关于'{topic}'的PPT，包含{slide_count}张幻灯片"
        except Exception as e:
            return "", False, f"生成PPT时出错: {str(e)}"
    
    @staticmethod
    def _parse_content_to_slides(document: Document, content: str) -> None:
        """解析内容并添加为幻灯片
        
        Args:
            document: 文档对象
            content: 要解析的内容
        """
        # 按照 ## 分割内容为幻灯片
        sections = content.split("\n## ")
        
        # 处理第一部分（可能包含标题页）
        first_section = sections[0]
        if first_section.startswith("# "):
            # 这是标题页
            title_lines = first_section.split("\n", 1)
            title = title_lines[0].replace("# ", "")
            content = title_lines[1] if len(title_lines) > 1 else ""
            document.add_slide(title, first_section, "title")
        else:
            # 普通页面
            document.add_slide("第1页", first_section)
        
        # 处理其余部分
        for i, section in enumerate(sections[1:], 1):
            title_lines = section.split("\n", 1)
            title = title_lines[0]
            content = title_lines[1] if len(title_lines) > 1 else ""
            document.add_slide(title, f"## {section}", "standard")
