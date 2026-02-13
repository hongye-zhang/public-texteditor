import asyncio
from collections import defaultdict
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from app.services.intent.top_level_intent_service import identify_top_level_intent

# 评估数据集：message 和 期望 top-level intent
TEST_DATA = [
    ("请帮我生成一份项目计划书", "create_new"),
    ("修改我上次写的报告", "modify_existing"),
    ("这行代码是什么意思？", "question_only"),
    ("插入一个图片", "insert_image"),
    ("读取我的简历并检查语法错误", "read_file"),
    ("其他", "other"),
    ("插入10个单词", "create_new"),
    ("write some words about film", "create_new"),
    ("第2段太长了", "modify_existing"),
    ("我在前面3段得出的结论正确吗？", "question_only"),
    ("第4段后面，应该添加一个示意图", "insert_image"),
    ("我想要一个专业版的合同，长度大约2000字", "create_new"),
    ("这个小说写得没意思", "create_new"),
    ("第4段写得不生动，细节太少", "modify_existing"),
    # 可以在这里自行扩展多条样本
]

# 要比较的模型列表
MODELS = ["gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o"]

async def evaluate_model(model_name: str):
    correct = 0
    total = len(TEST_DATA)

    for msg, expected in TEST_DATA:
        intent = await identify_top_level_intent(msg, model=model_name)
        pred = intent.intent_type
        print(f"[Model: {model_name}] \"{msg}\" -> {pred} (expected: {expected})")
        if pred == expected:
            correct += 1

    accuracy = correct / total if total else 0
    print(f"Model {model_name}: {correct}/{total} 正确, Accuracy: {accuracy:.2%}\n")
    return accuracy

async def main():
    results = {}
    for model in MODELS:
        print(f"Evaluating {model}...")
        acc = await evaluate_model(model)
        results[model] = acc

    print("最终评估结果:")
    for m, a in results.items():
        print(f"- {m}: {a:.2%}")

if __name__ == "__main__":
    asyncio.run(main())
