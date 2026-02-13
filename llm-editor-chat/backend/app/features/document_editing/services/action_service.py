from typing import List, Dict, Any
from typing import List, Dict, Any, Optional
import json
import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)
api_key = os.getenv("OPENAI_API_KEY")
if api_key is None:
    raise ValueError("OPENAI_API_KEY environment variable not found")


class ActionPlan(BaseModel):
    """Model for a planned editing action."""
    type: str = Field(description="Action type, e.g., 'insert', 'replace', 'delete'")
    payload: Dict[str, Any] = Field(description="Payload containing action details")


async def plan_edit_actions(
    intent_type: str,
    target_type: str,
    user_message: str,
    target_content: str = None
) -> List[ActionPlan]:
    """
    Plan a list of editing actions based on intent and target.

    Args:
        intent_type: The identified intent type (e.g., 'section_edit')
        target_type: The target type ('selected_text', 'whole_content', 'none')
        user_message: The original user message
        target_content: The content of the target text

    Returns:
        List[ActionPlan]: A list of planned actions
    """
    # 创建聊天模型
    chat = ChatOpenAI(
        api_key=api_key,
        model="gpt-4o",
        temperature=0.2
    )
    
    # TODO: integrate LLM or custom logic to generate real plans
    # For now, return a stub action
    '''action = ActionPlan(
        type='insert-text',
        payload={'content': '这是测试内容'}
    )
    return [action]'''
    # 准备系统提示
    system_prompt = """
你是一个文本编辑助手，负责规划编辑操作。根据用户的请求和目标文本，你需要生成一个或多个编辑动作。

支持的动作类型包括：
1. insert - 插入新内容
2. replace_all - 替换全部内容
3. delete - 删除内容

你的输出必须是一个有效的JSON数组，每个元素包含以下字段：
- type: 动作类型（insert、replace_all、delete等）
- payload: 包含动作详情的对象，例如：
  - 对于insert: {"content": "要插入的内容"}
  - 对于replace_all: {"content": "替换后的内容"}
  - 对于delete: {}

示例输出：
```json
[
  {
    "type": "replace_all",
    "payload": {
      "content": "这是修改后的内容"
    }
  }
]
```

请确保你的输出是一个有效的JSON数组，并且每个动作都有明确的类型和必要的参数。
"""
    
    # 准备用户消息
    content_preview = ""
    if target_content:
        # 限制内容长度，避免token过多
        content_preview = target_content[:1000] + "..." if len(target_content) > 1000 else target_content
    
    user_prompt = f"""
用户请求: {user_message}

目标类型: {target_type}

目标内容:
{content_preview}

请根据用户请求和目标内容，生成适当的编辑动作。
"""
    
    # 创建消息
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # 调用模型
    response = await chat.ainvoke(messages)
    
    # 解析响应
    try:
        content = response.content
        # 提取JSON
        if "```json" in content and "```" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()
            
        # 解析JSON
        actions_data = json.loads(json_str)
        
        # 验证并转换为ActionPlan对象
        actions = []
        for action_data in actions_data:
            if "type" in action_data and "payload" in action_data:
                actions.append(ActionPlan(**action_data))
        
        if actions:
            return actions
        
    except Exception as e:
        print(f"Error parsing action plan: {e}")
    
    # 如果解析失败或没有有效动作，返回默认动作
    return [ActionPlan(
        type='replace_all',
        payload={'content': f"我已根据您的请求：'{user_message}' 处理了内容，但无法生成具体的编辑动作。"}
    )]

    
