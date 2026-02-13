import pytest
import pytest_asyncio
import sys, os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.intent.top_level_intent_service import identify_top_level_intent

@ pytest.mark.asyncio
@ pytest.mark.parametrize("msg,expected", [
    ("请帮我生成一份项目计划书", "create_new"),
    ("修改我上次写的报告",   "modify_existing"),
    ("这行代码是什么意思？", "question_only"),
])
async def test_identify_top_level_intent(msg, expected, monkeypatch):
    """
    测试 identify_top_level_intent，使用 monkeypatch 模拟 LLM 调用返回
    """
    # 构造假返回 JSON，仅包含必要字段
    fake_json = {
        "intent_type": expected,
        "confidence": 0.9,
        "additional_info": None
    }
    fake_content = json.dumps(fake_json)

    # 模拟响应对象
    class FakeResponse:
        def __init__(self, content):
            self.content = content

    # 模拟 ChatOpenAI.ainvoke 方法
    async def fake_ainvoke(self, messages):
        return FakeResponse(fake_content)

    # 替换 ChatOpenAI.ainvoke
    monkeypatch.setattr(
        "app.services.top_level_intent_service.ChatOpenAI.ainvoke",
        fake_ainvoke
    )

    # 调用被测试异步函数
    result = await identify_top_level_intent(msg, model="gpt-4.1-mini")
    assert result.intent_type == expected
