import pytest
import pytest_asyncio
import sys, os
import json
# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.services.intent.insert_image_intent_service import identify_insert_image_intent, InsertImageIntent

@pytest.mark.asyncio
@pytest.mark.parametrize("msg,image_type", [
    ("插入一张风景照片，最好是高清的", "aesthetic"),
    ("帮我画一个函数y=sin(x)的示意图", "conceptual"),
    ("给我一张公司Logo的插图", "aesthetic"),
    ("请生成一个流程示意图", "conceptual"),
    ("插入一个讲解光线折射的图", "conceptual"),
    ("黑白线条画，带着颜色块", "aesthetic")
])
async def test_identify_insert_image_intent(msg, image_type, monkeypatch):
    """
    Test identify_insert_image_intent with mocked ChatOpenAI.ainvoke
    """
    fake_json = {
        "image_type": image_type,
        "confidence": 0.92,
        "additional_info": None
    }
    fake_content = json.dumps(fake_json)

    class FakeResponse:
        def __init__(self, content):
            self.content = content

    async def fake_ainvoke(self, messages):
        return FakeResponse(fake_content)

    monkeypatch.setattr(
        "app.services.intent.insert_image_intent_service.ChatOpenAI.ainvoke",
        fake_ainvoke
    )

    result = await identify_insert_image_intent(msg, model="gpt-4.1-mini")
    assert isinstance(result, InsertImageIntent)
    assert result.image_type == image_type
    assert 0.0 <= result.confidence <= 1.0
