from typing import Optional, Dict, Any, Tuple
import re

class CommandAction:
    """命令动作类"""
    def __init__(self, action_type: str, parameters: Dict[str, Any]):
        self.action_type = action_type
        self.parameters = parameters
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "action_type": self.action_type,
            "parameters": self.parameters
        }

class CommandParsingService:
    """命令解析服务"""
    
    @staticmethod
    def parse_command(command: str, document_content: Optional[str] = None, 
                     selected_text: Optional[str] = None, 
                     selection_start: Optional[int] = None, 
                     selection_end: Optional[int] = None) -> Tuple[Optional[CommandAction], bool, str, bool]:
        """解析自然语言命令
        
        Args:
            command: 命令字符串
            document_content: 文档内容
            selected_text: 选中的文本
            selection_start: 选择开始位置
            selection_end: 选择结束位置
            
        Returns:
            Tuple[Optional[CommandAction], bool, str, bool]: (命令动作, 是否成功, 消息, 是否需要确认)
        """
        try:
            command = command.lower()
            
            # 文本选择命令
            if re.search(r"选择|选中|找到", command):
                return CommandParsingService._handle_selection_command(
                    command, document_content, selected_text, selection_start, selection_end
                )
            
            # 文本修改命令
            elif re.search(r"修改|替换|改为|更改", command):
                return CommandParsingService._handle_modification_command(
                    command, document_content, selected_text, selection_start, selection_end
                )
            
            # 格式化命令
            elif re.search(r"加粗|斜体|标题|引用|列表", command):
                return CommandParsingService._handle_formatting_command(
                    command, document_content, selected_text, selection_start, selection_end
                )
            
            # PPT/文档结构命令
            elif re.search(r"创建幻灯片|添加页面|新建页|生成ppt|制作ppt", command):
                return CommandParsingService._handle_document_command(
                    command, document_content, selected_text, selection_start, selection_end
                )
            
            # 如果无法识别命令
            return None, False, "无法识别的命令，请尝试使用更明确的指令", False
        except Exception as e:
            return None, False, f"解析命令时出错: {str(e)}", False
    
    @staticmethod
    def _handle_selection_command(command: str, document_content: Optional[str], 
                                 selected_text: Optional[str], 
                                 selection_start: Optional[int], 
                                 selection_end: Optional[int]) -> Tuple[Optional[CommandAction], bool, str, bool]:
        """处理文本选择命令"""
        # 选择第一段
        if re.search(r"选择第一段|选中第一段", command):
            action = CommandAction(
                action_type="select",
                parameters={"target": "first_paragraph"}
            )
            return action, True, "已解析选择第一段的命令", False
        
        # 选择标题
        elif re.search(r"选择标题|选中标题", command):
            action = CommandAction(
                action_type="select",
                parameters={"target": "heading"}
            )
            return action, True, "已解析选择标题的命令", False
        
        # 选择特定文本
        elif "选择" in command and "文本" in command:
            # 尝试提取要选择的文本
            match = re.search(r"选择[\"\'](.*?)[\"\']", command)
            if match:
                text_to_select = match.group(1)
                action = CommandAction(
                    action_type="select",
                    parameters={"target": "text", "text": text_to_select}
                )
                return action, True, f"已解析选择特定文本的命令", False
        
        # 如果无法识别具体的选择命令
        return None, False, "无法识别的选择命令，请尝试更明确的指令，例如'选择第一段'或'选择标题'", False
    
    @staticmethod
    def _handle_modification_command(command: str, document_content: Optional[str], 
                                    selected_text: Optional[str], 
                                    selection_start: Optional[int], 
                                    selection_end: Optional[int]) -> Tuple[Optional[CommandAction], bool, str, bool]:
        """处理文本修改命令"""
        # 检查是否有选中的文本
        if not selected_text:
            return None, False, "请先选择要修改的文本", False
        
        # 替换文本
        if "替换为" in command:
            # 尝试提取新文本
            match = re.search(r"替换为[\"\'](.*?)[\"\']", command)
            if match:
                new_text = match.group(1)
                action = CommandAction(
                    action_type="modify",
                    parameters={
                        "operation": "replace-text",
                        "new_text": new_text,
                        "start": selection_start,
                        "end": selection_end
                    }
                )
                return action, True, f"已解析替换文本的命令", True
        
        # 如果无法识别具体的修改命令
        return None, False, "无法识别的修改命令，请尝试更明确的指令，例如'替换为\"新文本\"'", False
    
    @staticmethod
    def _handle_formatting_command(command: str, document_content: Optional[str], 
                                  selected_text: Optional[str], 
                                  selection_start: Optional[int], 
                                  selection_end: Optional[int]) -> Tuple[Optional[CommandAction], bool, str, bool]:
        """处理格式化命令"""
        # 检查是否有选中的文本
        if not selected_text:
            return None, False, "请先选择要格式化的文本", False
        
        # 加粗文本
        if "加粗" in command:
            action = CommandAction(
                action_type="format",
                parameters={
                    "format_type": "bold",
                    "start": selection_start,
                    "end": selection_end
                }
            )
            return action, True, "已解析加粗文本的命令", False
        
        # 设置为标题
        elif "标题" in command:
            level = 1  # 默认为一级标题
            if "二级" in command or "2级" in command:
                level = 2
            elif "三级" in command or "3级" in command:
                level = 3
                
            action = CommandAction(
                action_type="format",
                parameters={
                    "format_type": f"heading{level}",
                    "start": selection_start,
                    "end": selection_end
                }
            )
            return action, True, f"已解析设置为{level}级标题的命令", False
        
        # 如果无法识别具体的格式化命令
        return None, False, "无法识别的格式化命令，请尝试更明确的指令，例如'加粗'或'设为二级标题'", False
    
    @staticmethod
    def _handle_document_command(command: str, document_content: Optional[str], 
                                selected_text: Optional[str], 
                                selection_start: Optional[int], 
                                selection_end: Optional[int]) -> Tuple[Optional[CommandAction], bool, str, bool]:
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
            
            action = CommandAction(
                action_type="create_document",
                parameters={
                    "document_type": "presentation",
                    "topic": topic,
                    "slide_count": slide_count
                }
            )
            return action, True, f"已解析创建PPT的命令，主题：{topic}，页数：{slide_count}", True
        
        # 添加幻灯片
        elif re.search(r"添加|新建", command) and re.search(r"页面|幻灯片|页", command):
            # 尝试提取标题
            title = "新页面"
            match = re.search(r"标题是[\"\'](.*?)[\"\']", command)
            if match:
                title = match.group(1)
            
            action = CommandAction(
                action_type="add_slide",
                parameters={
                    "title": title,
                    "content": ""  # 内容可以后续添加
                }
            )
            return action, True, f"已解析添加页面的命令，标题：{title}", False
        
        # 如果无法识别具体的文档命令
        return None, False, "无法识别的文档命令，请尝试更明确的指令，例如'创建关于\"AI\"的PPT'或'添加标题是\"方法\"的页面'", False
