"""
LLM工具函数使用示例

本脚本展示如何在实际应用中使用app/utils/llm_utils.py中的辅助函数
"""
import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from typing import List, Dict

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入LLM工具函数
from app.utils.llm_utils import generate_text, stream_text, generate_with_history


async def example_simple_generation():
    """简单文本生成示例"""
    logger.info("示例1: 简单文本生成")
    
    prompt = "请解释什么是依赖注入以及它的优点"
    system_message = "你是一个软件架构专家，擅长解释软件设计模式和原则。"
    
    logger.info(f"用户提示: {prompt}")
    
    response = await generate_text(
        prompt=prompt,
        system_message=system_message,
        temperature=0.7
    )
    
    logger.info(f"AI回复: {response}")
    logger.info("简单文本生成示例完成\n")


async def example_streaming_generation():
    """流式文本生成示例"""
    logger.info("示例2: 流式文本生成")
    
    messages = [
        {"role": "system", "content": "你是一个专业的技术文档编写者，擅长创建清晰简洁的API文档。"},
        {"role": "user", "content": "请为一个名为'calculate_statistics'的函数编写Python文档字符串，该函数接受一个数字列表，返回均值、中位数和标准差。"}
    ]
    
    logger.info(f"用户消息: {messages[1]['content']}")
    logger.info("开始流式生成...")
    
    # 在实际应用中，这里可能会将每个chunk发送到前端
    full_response = []
    async for chunk in stream_text(messages=messages, temperature=0.7):
        # 在实际应用中，这里会将chunk发送到前端
        # 这里只是模拟打印前10个字符，然后用...表示
        preview = chunk[:10] + "..." if len(chunk) > 10 else chunk
        logger.info(f"收到chunk: {preview}")
        full_response.append(chunk)
    
    complete_response = "".join(full_response)
    logger.info(f"完整回复: {complete_response[:100]}...")
    logger.info("流式文本生成示例完成\n")


async def example_conversation():
    """对话历史示例"""
    logger.info("示例3: 带对话历史的生成")
    
    # 模拟对话历史
    conversation_history = [
        {"role": "user", "content": "什么是RESTful API?"},
        {"role": "assistant", "content": "RESTful API是一种基于REST架构风格的应用程序接口，它使用HTTP请求来访问和操作数据。REST代表表述性状态转移，它是一种设计原则，而不是协议或标准。RESTful API通常使用HTTP方法如GET、POST、PUT和DELETE来执行操作，并使用JSON或XML格式传输数据。"}
    ]
    
    # 用户的后续问题
    user_message = "它与GraphQL有什么区别?"
    
    logger.info(f"历史问题: {conversation_history[0]['content']}")
    logger.info(f"历史回复: {conversation_history[1]['content'][:50]}...")
    logger.info(f"当前问题: {user_message}")
    
    # 使用带历史记录的生成函数
    response = await generate_with_history(
        user_message=user_message,
        conversation_history=conversation_history,
        system_message="你是一个Web开发专家，擅长解释API设计和网络技术。",
        temperature=0.7
    )
    
    logger.info(f"AI回复: {response[:100]}...")
    logger.info("对话历史示例完成\n")


async def example_custom_model():
    """使用自定义模型的示例"""
    logger.info("示例4: 使用自定义模型")
    
    # 检查是否有可用的自定义模型
    custom_model = os.getenv("CUSTOM_MODEL", "gpt-3.5-turbo")
    
    prompt = "请用Python编写一个简单的快速排序算法"
    
    logger.info(f"使用模型: {custom_model}")
    logger.info(f"用户提示: {prompt}")
    
    response = await generate_text(
        prompt=prompt,
        system_message="你是一个Python编程专家，擅长编写高效、易读的代码。",
        model=custom_model,  # 指定自定义模型
        temperature=0.3      # 降低温度以获得更确定性的回复
    )
    
    logger.info(f"AI回复: {response[:100]}...")
    logger.info("自定义模型示例完成\n")


async def main():
    """运行所有示例"""
    logger.info("开始运行LLM工具函数示例")
    
    try:
        # 按顺序运行示例
        await example_simple_generation()
        await example_streaming_generation()
        await example_conversation()
        await example_custom_model()
        
        logger.info("所有示例运行完成")
    except Exception as e:
        logger.error(f"运行示例时出错: {str(e)}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
