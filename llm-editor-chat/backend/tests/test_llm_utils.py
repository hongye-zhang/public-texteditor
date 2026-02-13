"""
测试LLM工具函数

测试app/utils/llm_utils.py中的辅助函数
"""
import asyncio
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

async def test_generate_text():
    """测试非流式文本生成函数"""
    from app.utils.llm_utils import generate_text
    
    print("测试非流式文本生成...")
    print(f"使用模型: {os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')}")
    
    prompt = "请用一句话解释量子计算"
    system_message = "你是一个专业的科学顾问，擅长简明扩要地解释复杂概念。"
    
    try:
        print("\n=== 用户提示 ===")
        print(f"User: {prompt}")
        
        # 调用非流式生成函数
        response = await generate_text(
            prompt=prompt,
            system_message=system_message,
            temperature=0.7
        )
        
        print("\n=== 助手回复 ===")
        print(f"Assistant: {response}")
        
        print("\n非流式生成测试完成!")
        return True
    except Exception as e:
        print(f"\n非流式生成测试出错: {str(e)}")
        return False

async def test_stream_text():
    """测试流式文本生成函数"""
    from app.utils.llm_utils import stream_text
    
    print("\n测试流式文本生成...")
    print(f"使用模型: {os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')}")
    
    messages = [
        {"role": "system", "content": "你是一个有创意的故事讲述者，擅长创作简短有趣的故事。请确保故事不超过三句话。"},
        {"role": "user", "content": "请用三句话讲一个关于太空探险的小故事。"}
    ]
    
    try:
        print(f"\n消息: {messages[1]['content']}")
        print("\n回复: ")
        
        # 收集全部内容，而不是实时打印，以避免与其他测试输出混合
        full_response = []
        async for chunk in stream_text(messages=messages, temperature=0.8):
            full_response.append(chunk)
        
        # 打印完整响应
        complete_response = "".join(full_response)
        print(complete_response)
        
        print("\n流式生成测试完成!")
        return True
    except Exception as e:
        print(f"\n流式生成测试出错: {str(e)}")
        return False

async def test_generate_with_history():
    """测试带历史记录的文本生成函数"""
    from app.utils.llm_utils import generate_with_history
    
    print("\n测试带历史记录的文本生成...")
    print(f"使用模型: {os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')}")
    
    # 模拟对话历史
    conversation_history = [
        {"role": "user", "content": "Python和JavaScript有什么区别?"},
        {"role": "assistant", "content": "Python是一种解释型、高级、通用的编程语言，以简洁易读的语法著称，常用于后端开发、数据分析和AI。JavaScript主要用于Web前端开发，是浏览器中的标准脚本语言，也可通过Node.js用于后端。"}
    ]
    
    user_message = "哪种语言更适合初学者?"
    
    try:
        print("\n=== 对话历史 ===")
        print(f"User: {conversation_history[0]['content']}")
        print(f"Assistant: {conversation_history[0]['content'][:50]}...")
        print("\n=== 当前问题 ===")
        print(f"User: {user_message}")
        
        # 调用带历史记录的生成函数
        system_message = "你是一个编程教育专家，擅长给初学者提供建议。请简明扩要地回答问题，不要超过200字。"
        response = await generate_with_history(
            user_message=user_message,
            conversation_history=conversation_history,
            system_message=system_message,
            temperature=0.7
        )
        
        print("\n=== 助手回复 ===")
        print(f"Assistant: {response}")
        
        print("\n带历史记录的生成测试完成!")
        return True
    except Exception as e:
        print(f"\n带历史记录的生成测试出错: {str(e)}")
        return False

async def run_all_tests():
    """按顺序运行所有测试"""
    print("\n======== 开始测试 LLM 工具函数 ========\n")
    
    # 按顺序运行测试，避免输出混乱
    test1_result = await test_generate_text()
    print("\n" + "-"*50 + "\n")
    
    test2_result = await test_stream_text()
    print("\n" + "-"*50 + "\n")
    
    test3_result = await test_generate_with_history()
    
    # 汇总测试结果
    results = [test1_result, test2_result, test3_result]
    all_passed = all(results)
    
    print("\n======== 测试结果摘要 ========")
    print(f"非流式文本生成: {'通过 ✓' if test1_result else '失败 ✗'}")
    print(f"流式文本生成: {'通过 ✓' if test2_result else '失败 ✗'}")
    print(f"带历史记录的生成: {'通过 ✓' if test3_result else '失败 ✗'}")
    print(f"总体结果: {'全部通过 ✓' if all_passed else '部分失败 ✗'}")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(run_all_tests())
