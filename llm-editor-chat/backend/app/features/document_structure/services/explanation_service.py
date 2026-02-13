"""
解释性反馈服务模块

提供生成文档修改解释的功能，帮助用户理解系统所做的修改。
"""
import logging
from typing import Optional

from app.utils.llm_utils import generate_text

logger = logging.getLogger(__name__)

async def generate_modification_explanation(
    original_content: str,
    modified_content: str,
    user_request: str,
    model: str = "gpt-4.1-mini",
    temperature: float = 0.3
) -> str:
    """
    生成文档修改的解释性反馈
    
    Args:
        original_content: 原始文档内容
        modified_content: 修改后的文档内容
        user_request: 用户的原始请求
        model: 使用的模型名称
        temperature: 温度参数
        
    Returns:
        解释性反馈文本
    """
    # 如果内容相同，则不需要解释
    if original_content == modified_content:
        return "No changes were made to the document."
    
    system_prompt = """You are a professional document revision expert. Your task is to analyze document changes and provide clear, concise explanations to help users understand the modifications and their rationale. Maintain a professional, objective tone and focus on the most important changes."""
    
    # 读取top_intent，然后读取language设置，并把语言设置添加到system_prompt之后
    from app.features.chat.router import get_current_intent
    
    # 获取当前的top_level_intent
    top_intent = get_current_intent()
    
    # 默认使用中文，如果top_intent存在且有language属性，则使用该属性
    language = "English"
    if top_intent and hasattr(top_intent, 'additional_info') and top_intent.additional_info:
        if isinstance(top_intent.additional_info, dict) and 'language' in top_intent.additional_info:
            language = top_intent.additional_info['language']
    
    system_prompt += f"Output in {language}."
    
    user_prompt = f"""Please analyze the following original document and incremental changes, along with the user's original request, and provide a concise explanation.

<User's Original Request>
{user_request}
</User's Original Request>

<Original Document>
{original_content[:1500]}  # Length limited to avoid token limit
</Original Document>

<Incremental Changes>
{modified_content[:1500]}  # Length limited to avoid token limit
</Incremental Changes>

IMPORTANT: The 'Incremental Changes' section contains a JSON array that ONLY shows paragraphs that were modified or added. It does NOT represent the complete modified document. Each object in this array has:
- "path": null (for modified paragraphs) or "new" (for newly added paragraphs)
- "content": the new content of the paragraph (empty string means no change to that paragraph)
- "id": the unique identifier of the paragraph

Empty content fields do NOT mean text was deleted - they represent paragraphs that were not changed. Only focus on paragraphs with actual content.

Please provide a concise explanation in 3 paragraphs:

1. Summary of Key Changes: 1-2 sentences summarizing the modifications made
2. Specific Changes: List the 2-3 most important specific changes (if applicable)
3. Rationale: How these changes address the user's request + direct benefits to the reader.

Response format requirements:
- Use clear, direct language
- Avoid using first-person pronouns like "I" or "we"
- Do not use redundant phrases like "as per your request" or "as you instructed"
- Keep the total word count around 50 words
- Do not include any additional explanations, notes, or greetings"""

    try:
        explanation = await generate_text(
            prompt=user_prompt,
            system_message=system_prompt,
            model=model,
            temperature=temperature,
            streaming=False
        )
        return explanation
    except Exception as e:
        logger.error(f"Error generating explanation: {e}")
        return "已根据您的要求修改了文档。"  # 出错时返回通用消息
