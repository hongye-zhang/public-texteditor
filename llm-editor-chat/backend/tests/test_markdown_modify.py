import re
import random

def add_paragraph_ids(markdown_text: str) -> str:
    """
    Add a unique 4-digit ID to each paragraph in the markdown text.
    
    Args:
        markdown_text: Input markdown text
        
    Returns:
        str: Modified markdown text with paragraph IDs
    """
    # Split the text into paragraphs (split by double newlines)
    paragraphs = markdown_text.split('\n\n')
    
    # Process each paragraph
    result = []
    used_ids = set()
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            result.append('')
            continue
            
        # Generate a unique 4-digit ID
        while True:
            # Generate a random 4-digit number as string
            para_id = f"{random.randint(0, 9999):04d}"
            if para_id not in used_ids:
                used_ids.add(para_id)
                break
                
        # Add the ID to the beginning of the paragraph
        modified_para = f"[ID:{para_id}] {paragraph}"
        result.append(modified_para)
    
    # Join the paragraphs back together
    return '\n\n'.join(result)

def test_add_paragraph_ids():
    """Test the add_paragraph_ids function with various markdown inputs."""
    # Test case 1: Simple paragraphs
    input_text = """This is the first paragraph.

This is the second paragraph.

And this is the third one."""
    
    output = add_paragraph_ids(input_text)
    print("Test 1 - Simple paragraphs:")
    print(output)
    
    # Test case 2: With markdown formatting
    input_text2 = """# Header 1

This is a paragraph with *italic* and **bold** text.

## Header 2

- List item 1
- List item 2
- List item 3

> Blockquote"""
    
    output2 = add_paragraph_ids(input_text2)
    print("\nTest 2 - With markdown formatting:")
    print(output2)
    
    # Test case 3: Empty input
    output3 = add_paragraph_ids("")
    print("\nTest 3 - Empty input:")
    print(f'"{output3}"')
    
    # Test case 4: Single line
    output4 = add_paragraph_ids("Just one line")
    print("\nTest 4 - Single line:")
    print(output4)

if __name__ == "__main__":
    # test_add_paragraph_ids()
    markdownstr = '''
    你说得对，刚才推荐的部分项目链接过时或者有误，非常感谢你的提醒！
其实，“结构化增量编辑+LLM”是近两年才兴起的领域，**大多数论文有原理和demo，但主流开源实现很少**。但**相关思路和原理在一些研究和部分工程实现中是可以找到明确论据的**。
我来补充下**真实存在且和你的思路高度相关的项目和文献**，并说明哪里可以查阅、借鉴思路。

---

## 1. **真实相关的开源项目**

### **A. [Blocksuite/affine](https://github.com/toeverything/AFFiNE)**

* **简介**：现代协作文档编辑器，采用块（Block）为最小单元，每个块有唯一 ID。支持结构化增量编辑、局部修订，未来有LLM插件（他们[公开讨论过token压缩与结构diff](https://community.toeverything.info/t/topic/345)）。
* **参考用法**：源码中所有块（node）都有 `id`，增量编辑时会精确定位和同步局部变更，**有利于 LLM 增量场景借鉴**。

### **B. [tldraw/tldraw](https://github.com/tldraw/tldraw)**

* **简介**：图形/文本协作编辑器，每个元素（包括文本）都有唯一 id，局部操作和“结构化同步”是核心技术之一。
* **启发**：tldraw 用于 AI 增量标注、部分 LLM 编辑实验，主打就是“最小可编辑单元+唯一 id+增量更新”。

### **C. [RemNote/RemNote](https://github.com/remnoteio/remnote-oss)**

* **简介**：基于块和层级文档，所有节点有唯一 id，并已支持 LLM 相关插件开发，增量编辑机制高度结构化。

---

## 2. **相关的论文与原理**

### **A. 结构化diff/增量编辑结合LLM的论文**

* **《Token-Efficient Text Editing with Large Language Models》**
  [arXiv:2312.06829](https://arxiv.org/abs/2312.06829)

  > “…edit operations are represented as position-anchored diffs, sending only changed fragments (with ids/anchors) to LLMs…”
* **《Hierarchical Editing with Large Language Models》**
  [arXiv:2310.09198](https://arxiv.org/abs/2310.09198)

  > “…by structuring document as a tree of nodes with unique ids, only affected subtrees are passed to the LLM, achieving significant token savings…”

### **B. 技术博客/原理探讨**

* **OpenAI 官方博客/社区**

  * 讨论 token 优化/增量上下文、编辑 anchor/id 等最佳实践，例如
    [OpenAI community: “Efficient LLM document editing”](https://community.openai.com/t/why-not-send-full-document-to-llms-efficient-document-editing/629201)

---

## 3. **工程实现的通用思路总结**

**虽然没有专门的“LLM结构化增量编辑”项目成为主流库，但：**

* 各种富文本协作编辑器（AFFiNE, tldraw, RemNote, Logseq等）都采用块ID追踪、结构化diff，这些机制与LLM集成只需一层“diff-prompt”即可（即只将有id的diff片段+上下文送LLM）。
* LLM增量编辑是2023–2024快速发展中的领域，**论文和产品demo远多于开源库**。你若要工程落地，建议参考 AFFiNE 或 RemNote 的 node id 管理和局部 diff 机制，自行封装与 LLM API 的结合。

---

## 4. **补充说明**

* 你要找的就是“node有唯一ID，局部diff只送有ID的片段到LLM”，而不是每次全量上下文送LLM。
* 这种思路已经有前沿论文和多个知名编辑器工程借鉴，并在社区和产品原理中反复被验证有效性。

---

### **如果你有更具体的应用场景（如针对ProseMirror/Tiptap二次开发），也可以提供下需求，我能帮你梳理代码方案或更具体地定位到哪个工程实现有借鉴价值。**

---

**如果你需要更多“真实存在”的源码案例或详细解读上述论文的技术方案，可以进一步告诉我！**

    '''

    convertstr = add_paragraph_ids(markdownstr)
    print(convertstr)
    
