import pytest
import pytest_asyncio
import sys, os
import json
# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.services.intent.modify_existing_intent_service import identify_modify_existing_intent, ModifyExistingIntent

@ pytest.mark.asyncio
@ pytest.mark.parametrize("msg,action", [
    ("在第3节前面插入一段总结", "insert"),
    ("把摘要替换成新的摘要", "replace"),
    ("在结论后面添加一段", "insert"),
    ("搜索 '风险' 并删除相关段落", "delete"),
    ("第2章写得太长，要精简下", "replace"),
    ("第5页，换一个例子", "replace"),
    ("第2.4小节，删掉", "delete"),
])
async def test_identify_modify_existing_intent(msg, action, monkeypatch):
    """
    Test identify_modify_existing_intent with mocked ChatOpenAI.ainvoke
    """
    fake_json = {
        "action": action,
        "confidence": 0.9,
        "additional_info": None
    }
    fake_content = json.dumps(fake_json)

    class FakeResponse:
        def __init__(self, content):
            self.content = content

    async def fake_ainvoke(self, messages):
        return FakeResponse(fake_content)

    monkeypatch.setattr(
        "app.services.intent.modify_existing_intent_service.ChatOpenAI.ainvoke",
        fake_ainvoke
    )

    result = await identify_modify_existing_intent(msg, model="gpt-4.1-mini")
    assert isinstance(result, ModifyExistingIntent)
    assert result.action == action
    assert 0.0 <= result.confidence <= 1.0
