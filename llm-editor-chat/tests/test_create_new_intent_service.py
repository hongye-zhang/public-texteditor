import pytest
import pytest_asyncio
import sys, os
import json
# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.services.intent.create_new_intent_service import identify_create_new_intent, CreateNewIntent

@ pytest.mark.asyncio
@ pytest.mark.parametrize("msg,doc_type,complexity,word_count", [
    ("请帮我新建一份简历，要求专业，200字左右", "resume", "professional", 200),
    ("帮我写个8页的PPT，简单介绍公司", "ppt", "simple", 1000),
    ("我要一份合同，大约1500字", "contract", "professional", 1500),
    ("写一个3页的ppt", "ppt", "simple", 300),
    ("写一份简历", "resume", "simple", 500),
    ("写一个毕业论文", "article", "professional", 10000),
    ("写一份这个pdf文件的精炼版本", "Refined version", "professional", 5000)
])
async def test_identify_create_new_intent(msg, doc_type, complexity, word_count, monkeypatch):
    """
    Test identify_create_new_intent with mocked ChatOpenAI.ainvoke
    """
    # Fake JSON response
    fake_json = {
        "document_type": doc_type,
        "complexity": complexity,
        "word_count": word_count,
        "confidence": 0.95,
        "additional_info": None
    }
    fake_content = json.dumps(fake_json)

    # Fake response object
    class FakeResponse:
        def __init__(self, content):
            self.content = content

    # Mock ainvoke
    async def fake_ainvoke(self, messages):
        return FakeResponse(fake_content)

    monkeypatch.setattr(
        "app.services.intent.create_new_intent_service.ChatOpenAI.ainvoke",
        fake_ainvoke
    )

    # Call and assert
    result = await identify_create_new_intent(msg, model="gpt-4.1-mini")
    assert isinstance(result, CreateNewIntent)
    assert result.document_type == doc_type
    assert result.complexity == complexity
    assert result.word_count == word_count
    assert 0.0 <= result.confidence <= 1.0
