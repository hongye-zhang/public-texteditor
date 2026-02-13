from typing import Optional, Dict, Any, Tuple

class TextSelectionService:
    """文本选择服务"""
    
    @staticmethod
    def select_by_position(document_content: str, start_position: int, end_position: int) -> Tuple[str, bool, str]:
        """根据位置选择文本
        
        Args:
            document_content: 文档内容
            start_position: 开始位置
            end_position: 结束位置
            
        Returns:
            Tuple[str, bool, str]: (选中的文本, 是否成功, 消息)
        """
        try:
            if start_position < 0 or end_position > len(document_content) or start_position >= end_position:
                return "", False, "无效的位置范围"
            
            selected_text = document_content[start_position:end_position]
            return selected_text, True, "文本已成功选择"
        except Exception as e:
            return "", False, f"选择文本时出错: {str(e)}"
    
    @staticmethod
    def select_by_content(document_content: str, search_text: str) -> Tuple[str, int, int, bool, str]:
        """根据内容查找并选择文本
        
        Args:
            document_content: 文档内容
            search_text: 要查找的文本
            
        Returns:
            Tuple[str, int, int, bool, str]: (选中的文本, 开始位置, 结束位置, 是否成功, 消息)
        """
        try:
            start_pos = document_content.find(search_text)
            if start_pos == -1:
                return "", -1, -1, False, f"找不到文本: '{search_text}'"
            
            end_pos = start_pos + len(search_text)
            return search_text, start_pos, end_pos, True, "文本已成功选择"
        except Exception as e:
            return "", -1, -1, False, f"选择文本时出错: {str(e)}"
    
    @staticmethod
    def select_by_command(document_content: str, command: str) -> Tuple[str, int, int, bool, str]:
        """根据命令选择文本
        
        Args:
            document_content: 文档内容
            command: 命令字符串
            
        Returns:
            Tuple[str, int, int, bool, str]: (选中的文本, 开始位置, 结束位置, 是否成功, 消息)
        """
        try:
            command = command.lower()
            
            # 选择第一段
            if "选择第一段" in command or "选中第一段" in command:
                paragraphs = document_content.split("\n\n")
                if not paragraphs:
                    return "", -1, -1, False, "文档中没有段落"
                
                first_para = paragraphs[0]
                start_pos = document_content.find(first_para)
                end_pos = start_pos + len(first_para)
                return first_para, start_pos, end_pos, True, "已选择第一段"
            
            # 选择标题
            elif "选择标题" in command or "选中标题" in command:
                lines = document_content.split("\n")
                for line in lines:
                    if line.strip().startswith("#"):
                        start_pos = document_content.find(line)
                        end_pos = start_pos + len(line)
                        return line, start_pos, end_pos, True, "已选择标题"
                return "", -1, -1, False, "文档中没有标题"
            
            # 选择特定文本
            import re
            match = re.search(r"选择[\"\'](.*?)[\"\']", command)
            if match:
                text_to_select = match.group(1)
                return TextSelectionService.select_by_content(document_content, text_to_select)
            
            return "", -1, -1, False, "无法理解命令或找不到匹配的文本"
        except Exception as e:
            return "", -1, -1, False, f"处理命令时出错: {str(e)}"
