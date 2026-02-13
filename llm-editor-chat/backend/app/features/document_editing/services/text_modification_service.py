from typing import Optional, Dict, Any, Tuple

class TextModificationService:
    """文本修改服务"""
    
    @staticmethod
    def modify_text(document_content: str, start_position: int, end_position: int, new_content: str) -> Tuple[str, bool, str]:
        """修改选定的文本
        
        Args:
            document_content: 文档内容
            start_position: 开始位置
            end_position: 结束位置
            new_content: 新内容
            
        Returns:
            Tuple[str, bool, str]: (修改后的完整文档内容, 是否成功, 消息)
        """
        try:
            if start_position < 0 or end_position > len(document_content) or start_position > end_position:
                return document_content, False, "无效的位置范围"
            
            # 替换指定位置的文本
            modified_content = document_content[:start_position] + new_content + document_content[end_position:]
            return modified_content, True, "文本已成功修改"
        except Exception as e:
            return document_content, False, f"修改文本时出错: {str(e)}"
    
    @staticmethod
    def format_text(document_content: str, start_position: int, end_position: int, format_type: str) -> Tuple[str, str, bool, str]:
        """格式化选定的文本
        
        Args:
            document_content: 文档内容
            start_position: 开始位置
            end_position: 结束位置
            format_type: 格式类型 (bold, italic, heading1, etc.)
            
        Returns:
            Tuple[str, str, bool, str]: (修改后的完整文档内容, 格式化后的文本片段, 是否成功, 消息)
        """
        try:
            if start_position < 0 or end_position > len(document_content) or start_position >= end_position:
                return document_content, "", False, "无效的位置范围"
            
            # 获取要格式化的文本
            text_to_format = document_content[start_position:end_position]
            
            # 应用格式
            format_mapping = {
                "bold": lambda text: f"**{text}**",
                "italic": lambda text: f"*{text}*",
                "heading1": lambda text: f"# {text}",
                "heading2": lambda text: f"## {text}",
                "heading3": lambda text: f"### {text}",
                "code": lambda text: f"`{text}`",
                "blockquote": lambda text: f"> {text}",
            }
            
            if format_type not in format_mapping:
                return document_content, text_to_format, False, f"不支持的格式类型: {format_type}"
            
            formatted_text = format_mapping[format_type](text_to_format)
            
            # 替换原文本
            modified_content = document_content[:start_position] + formatted_text + document_content[end_position:]
            
            return modified_content, formatted_text, True, f"文本已成功格式化为{format_type}"
        except Exception as e:
            return document_content, "", False, f"格式化文本时出错: {str(e)}"
    
    @staticmethod
    def modify_by_command(document_content: str, command: str, start_position: int, end_position: int) -> Tuple[str, str, bool, str]:
        """根据命令修改文本
        
        Args:
            document_content: 文档内容
            command: 命令字符串
            start_position: 开始位置
            end_position: 结束位置
            
        Returns:
            Tuple[str, str, bool, str]: (修改后的完整文档内容, 修改后的文本片段, 是否成功, 消息)
        """
        try:
            if start_position < 0 or end_position > len(document_content) or start_position >= end_position:
                return document_content, "", False, "无效的位置范围"
            
            # 获取要修改的文本
            selected_text = document_content[start_position:end_position]
            command = command.lower()
            
            # 加粗文本
            if "加粗" in command:
                formatted_text = f"**{selected_text}**"
                modified_content = document_content[:start_position] + formatted_text + document_content[end_position:]
                return modified_content, formatted_text, True, "已将文本加粗"
            
            # 设置为标题
            elif "标题" in command:
                heading_level = 1
                if "二级" in command or "2级" in command:
                    heading_level = 2
                elif "三级" in command or "3级" in command:
                    heading_level = 3
                
                prefix = "#" * heading_level + " "
                formatted_text = f"{prefix}{selected_text}"
                modified_content = document_content[:start_position] + formatted_text + document_content[end_position:]
                return modified_content, formatted_text, True, f"已将文本设为{heading_level}级标题"
            
            # 替换文本
            elif "替换" in command:
                import re
                match = re.search(r"替换为[\"\'](.*?)[\"\']", command)
                if match:
                    new_text = match.group(1)
                    modified_content = document_content[:start_position] + new_text + document_content[end_position:]
                    return modified_content, new_text, True, f"已将文本替换为: {new_text}"
            
            return document_content, selected_text, False, "无法理解命令或无法执行修改操作"
        except Exception as e:
            return document_content, "", False, f"处理命令时出错: {str(e)}"
