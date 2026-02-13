"""
测试新的thinking流水线的简单脚本
"""
import asyncio
from backend.app.features.llm.services.router import stream_llm_response

async def test_pipeline():
    """测试流水线处理"""
    print("开始测试thinking流水线...")
    
    # 调用stream_llm_response函数，它会使用我们的新流水线
    async for message in stream_llm_response(
        system_prompt="测试系统提示词",
        user_message="测试用户消息",
    ):
        print(f"收到消息: {message}")
    
    print("测试完成")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
