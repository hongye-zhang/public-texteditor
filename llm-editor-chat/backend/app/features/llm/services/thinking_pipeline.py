"""
思考流水线模块。
实现基于Python的多阶段处理流水线，用于替代LLM直接输出thinking过程。
"""
import asyncio
from typing import Dict, Any, AsyncGenerator, Optional
from app.features.intent_analysis.services.intent_service import identify_document_intent
from app.features.intent_analysis.services.top_level_intent_service import identify_top_level_intent, TopLevelIntent
from app.features.intent_analysis.services.modify_existing_intent_service import identify_modify_existing_intent
from app.features.document_editing.services.target_service import identify_text_target
from app.features.document_editing.services.action_service import plan_edit_actions
from app.features.command_parsing.services.execution_service import execute_actions

async def process_user_input(
    user_message: str, 
    editor_content: Optional[str] = None, 
    selected_text: Optional[str] = None,
    top_level_intent: Optional[TopLevelIntent] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    处理用户输入的主流水线函数
    
    Args:
        user_message: 用户消息
        editor_content: 编辑器内容
        selected_text: 选中的文本
        top_level_intent: 已识别的顶层意图（可选）
        
    Yields:
        Dict: 包含类型和内容的消息字典
    """
    # 阶段1: 意图识别（顶层和二级意图）
    if top_level_intent:
        # 如果已有顶层意图，直接使用
        yield {"type": "thinking", "content": f"已识别您的意图：{top_level_intent.intent_type}（置信度 {top_level_intent.confidence:.2f}）"}
    else:
        # 否则重新识别顶层意图
        yield {"type": "thinking", "content": "正在分析您的请求..."}
        top_level_intent = await identify_top_level_intent(user_message)
        yield {"type": "thinking", "content": f"已识别您的意图：{top_level_intent.intent_type}（置信度 {top_level_intent.confidence:.2f}）"}
    
    # 根据顶层意图类型，获取二级意图
    if top_level_intent.intent_type == "modify_existing":
        # 获取修改意图的详细信息
        modify_intent = await identify_modify_existing_intent(user_message)
        yield {"type": "thinking", "content": f"修改类型：{modify_intent.action}，内容：{modify_intent.content}"}
        # 使用修改意图的内容进行后续处理
        intent_type = "section_edit"  # 默认使用section_edit作为文档类型
    else:
        # 对于其他类型，使用文档类型意图识别
        doc_intent = await identify_document_intent(user_message)
        yield {"type": "thinking", "content": f"文档类型：{doc_intent.document_type}（置信度 {doc_intent.confidence:.2f}）"}
        intent_type = doc_intent.document_type
    
    # 阶段2: 文本目标定位
    yield {"type": "thinking", "content": "正在定位编辑目标..."}
    target = await identify_text_target(user_message, editor_content, selected_text)
    if target.target_type == 'selected_text':
        yield {"type": "thinking", "content": "目标：选中的文本"}
    elif target.target_type == 'whole_content':
        yield {"type": "thinking", "content": "目标：全文内容"}
    else:
        yield {"type": "thinking", "content": "未找到编辑目标，使用默认上下文"}
    # 阶段3: 动作规划
    yield {"type": "thinking", "content": "正在规划编辑动作..."}
    actions = await plan_edit_actions(
        intent_type=intent_type,
        target_type=target.target_type,
        user_message=user_message,
        target_content=target.content
    )
    # 输出规划结果
    for plan in actions:
        yield {"type": "thinking", "content": f"已生成动作：{plan.type}"}
    # 阶段4: 执行动作并生成最终编辑结果
    # 使用执行服务将动作应用到目标内容
    updated = await execute_actions(
        original_content=target.content or "",
        actions=[plan.dict() for plan in actions]
    )
    # 输出最终编辑动作，将整个目标内容替换
    yield {"type": "action", "content": "编辑已应用", "action": {"type": "replace_all", "payload": {"content": updated}}}
    return
