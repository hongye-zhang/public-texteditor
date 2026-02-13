"""
简单测试脚本，直接测试thinking_pipeline模块
"""
import asyncio
from backend.app.features.llm.services.thinking_pipeline import process_user_input

async def main():
    print("开始测试thinking流水线...")
    
    async for message in process_user_input("测试用户消息"):
        print(f"收到消息: {message}")
    
    print("测试完成")

if __name__ == "__main__":
    asyncio.run(main())
