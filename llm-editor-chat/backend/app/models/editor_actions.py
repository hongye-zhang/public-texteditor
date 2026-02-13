"""
编辑器动作类型定义
基于共享的 editor_actions.json 文件自动生成
"""
import json
import os
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field

# 加载JSON定义
json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                         'shared', 'editor_actions.json')
with open(json_path, 'r', encoding='utf-8') as f:
    action_definitions = json.load(f)


class EditorActionType:
    """编辑器动作类型枚举"""
    pass


# 动态添加枚举值
for key, value in action_definitions['actions'].items():
    setattr(EditorActionType, key.upper(), value['type'])


class EditorActionPayload(BaseModel):
    """基础动作载荷"""
    content: str
    partial: Optional[bool] = False


class ReplaceTextPayload(EditorActionPayload):
    """替换文本动作载荷"""
    start: int
    end: int


def is_valid_action_type(action_type: str) -> bool:
    """验证动作类型是否有效"""
    valid_types = [a['type'] for a in action_definitions['actions'].values()]
    return action_type in valid_types


def is_valid_action(action: Dict[str, Any]) -> bool:
    """验证动作对象是否有效"""
    if not isinstance(action, dict) or 'type' not in action or 'payload' not in action:
        return False
    
    # 检查类型是否有效
    if not is_valid_action_type(action['type']):
        return False
    
    # 获取该类型动作的定义
    action_key = None
    for key, value in action_definitions['actions'].items():
        if value['type'] == action['type']:
            action_key = key
            break
    
    if not action_key:
        return False
    
    # 验证payload是否符合schema
    schema = action_definitions['actions'][action_key]['payload_schema']
    payload = action['payload']
    
    # 检查必填字段
    for field, type_def in schema.items():
        # 可选字段以?结尾
        is_optional = type_def.endswith('?')
        base_type = type_def[:-1] if is_optional else type_def
        
        # 如果字段不存在且不是可选的，则无效
        if field not in payload and not is_optional:
            return False
        
        # 如果字段存在，检查类型
        if field in payload:
            if base_type == 'string' and not isinstance(payload[field], str):
                return False
            elif base_type == 'number' and not isinstance(payload[field], (int, float)):
                return False
            elif base_type == 'boolean' and not isinstance(payload[field], bool):
                return False
    
    return True


def create_action(action_type: str, **payload) -> Dict[str, Any]:
    """根据类型创建动作对象"""
    # 验证动作类型
    if not is_valid_action_type(action_type):
        raise ValueError(f"Invalid action type: {action_type}")
    
    return {
        "type": action_type,
        "payload": payload
    }


def create_insert_text_action(content: str, position: str = 'cursor', partial: bool = False) -> Dict[str, Any]:
    """创建插入文本动作，支持位置：cursor、start、end"""
    return create_action(EditorActionType.INSERT_TEXT, content=content, position=position, partial=partial)


def create_replace_text_action(content: str, start: int, end: int, partial: bool = False) -> Dict[str, Any]:
    """创建替换文本动作"""
    return create_action(EditorActionType.REPLACE_TEXT, content=content, start=start, end=end, partial=partial)


def create_delete_text_action(start: int, end: int, partial: bool = False) -> Dict[str, Any]:
    """创建删除文本动作"""
    return create_action(EditorActionType.DELETE_TEXT, start=start, end=end, partial=partial)


def create_replace_all_action(content: str, partial: bool = False) -> Dict[str, Any]:
    """创建替换全部内容动作"""
    return create_action(EditorActionType.REPLACE_ALL, content=content, partial=partial)
