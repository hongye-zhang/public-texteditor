from typing import Optional, Literal
from pydantic import BaseModel
from app.features.intent_analysis.services.modify_existing_intent_service import ModifyExistingIntent


class TextTarget(BaseModel):
    """Model for identified text target in editor."""
    target_type: str  # 'selected_text', 'whole_content', 'none'
    content: Optional[str] = None


class ModifyTextTarget(BaseModel):
    """Model for modification target including scope and position."""
    target_type: Literal['section','search_query','selected_text','whole_content','cursor']
    section: Optional[str] = None
    search_query: Optional[str] = None
    content: Optional[str] = None
    location: Optional[Literal['before','after','replace']] = None


async def identify_text_target(
    user_message: str,
    editor_content: Optional[str] = None,
    selected_text: Optional[str] = None
) -> TextTarget:
    """
    Identify the target text for editing based on user selection or full content.

    Args:
        user_message: 用户消息（可用于后续扩展）
        editor_content: 编辑器所有内容
        selected_text: 选中的文本

    Returns:
        TextTarget: 包含目标类型与内容
    """
    if selected_text and selected_text.strip():
        return TextTarget(target_type='selected_text', content=selected_text)
    if editor_content and editor_content.strip():
        return TextTarget(target_type='whole_content', content=editor_content)
    return TextTarget(target_type='none', content=None)


async def identify_modify_target(
    intent: ModifyExistingIntent,
    editor_content: Optional[str] = None,
    selected_text: Optional[str] = None
) -> ModifyTextTarget:
    """
    Identify modification scope and position based on parsed intent.
    """
    # Extract search_query and location from additional_info
    search_query = None
    section = None
    location = None
    
    if isinstance(intent.additional_info, dict):
        search_query = intent.additional_info.get('search_query')
        section = intent.additional_info.get('section')
        location = intent.additional_info.get('location')
    
    # Search query based target
    if search_query:
        return ModifyTextTarget(
            target_type='search_query',
            section=None,
            search_query=search_query,
            content=editor_content,
            location=location
        )
    # Section based target
    if section:
        return ModifyTextTarget(
            target_type='section',
            section=section,
            search_query=None,
            content=editor_content,
            location=location
        )
    # Fallback to selected or whole content
    if selected_text and selected_text.strip():
        return ModifyTextTarget(
            target_type='selected_text',
            content=selected_text,
            location=location
        )
    if editor_content and editor_content.strip():
        return ModifyTextTarget(
            target_type='whole_content',
            content=editor_content,
            location=location
        )
    return ModifyTextTarget(
        target_type='cursor',
        content=None
    )
