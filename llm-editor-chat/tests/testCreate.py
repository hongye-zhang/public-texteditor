# 安装所需库（首次运行）
# pip install openai langchain pydantic

from pydantic import BaseModel
from typing import Optional
from langchain_openai import ChatOpenAI  # Updated import from langchain_openai
from langchain.output_parsers import PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re

# ===== 1. 定义结构提取模型 =====
class PPTRequest(BaseModel):
    topic: str
    use: str
    pages: int
    style: str
    structure_notes: Optional[str] = None
    words_per_page: Optional[int] = None

# ===== 2. 用户输入（原始）=====
user_input = """我想做一个介绍大语言模型在教育中的应用的PPT，给内部产品组汇报用，大概做个五、六页吧，内容尽量通俗，每页别写太多，结构上我希望有背景、趋势、场景、未来几个模块。"""

# ===== 3. 提取结构信息的函数 =====
from prompts.ppt_prompts import PPTPrompts

def extract_ppt_structure(user_input, model="gpt-4o", temperature=0):
    """从用户输入中提取PPT结构信息
    
    Args:
        user_input: 用户的原始输入文本
        model: 使用的语言模型名称
        temperature: 模型生成的多样性参数
        
    Returns:
        PPTRequest: 解析后的结构数据
    """
    # 使用静态方法类中的提取结构信息的 Prompt
    optimized_system_prompt = PPTPrompts.structure_extraction_prompt()

    # LangChain 结构提取
    parser = PydanticOutputParser(pydantic_object=PPTRequest)

    # 使用静态方法类中的格式说明
    format_instructions = PPTPrompts.format_instructions()

    # 创建消息
    system_message = SystemMessage(content=optimized_system_prompt)
    human_message = HumanMessage(content=f"{user_input}\n\nPlease output in the following format:\n{format_instructions}")

    # 使用LLM调用
    llm = ChatOpenAI(model=model, temperature=temperature)
    response_extract = llm.invoke([system_message, human_message])
    
    # 解析响应内容
    return parser.parse(response_extract.content)

# 调用函数提取结构信息
request_data = extract_ppt_structure(user_input)

# ===== 4. 结构大纲生成 Prompt =====
# Extract JSON from potential markdown code block
def extract_json_from_markdown(text):
    # Try to find JSON content in markdown code blocks
    json_code_block_pattern = r'```(?:json)?\n(.+?)\n```'
    match = re.search(json_code_block_pattern, text, re.DOTALL)
    
    if match:
        # Return the content inside the code block
        return match.group(1)
    else:
        # If no code block found, return the original text
        return text
        
def generate_ppt_structure(request_data, model="gpt-4o", temperature=0):
    """生成PPT的结构大纲
    
    Args:
        request_data: 用户请求数据，包含主题、页数等信息
        model: 使用的语言模型名称
        temperature: 模型生成的多样性参数
        
    Returns:
        dict: 包含原始的section结构和扁平化的页面列表
    """
    # 使用静态方法类中的结构大纲生成 Prompt
    structure_prompt = PPTPrompts.structure_prompt(request_data)
    
    # 创建HumanMessage并调用LLM
    structure_message = HumanMessage(content=structure_prompt)
    llm = ChatOpenAI(model=model, temperature=temperature)
    structure_response = llm.invoke([structure_message])
    
    # 提取和解析JSON响应
    json_content = extract_json_from_markdown(structure_response.content)
    section_structure = json.loads(json_content)
    
    # 创建一个扁平化的页面列表，用于兼容现有代码
    flat_pages = []
    for section in section_structure:
        for page in section['pages']:
            # 添加section信息到页面对象
            page['section'] = section['section']
            flat_pages.append(page)
    
    # 按页码排序
    flat_pages.sort(key=lambda x: x['page'])
    
    # 返回原始的section结构和扁平化的页面列表
    return {
        'sections': section_structure,
        'pages': flat_pages
    }

# 调用函数生成PPT结构
structure_data = generate_ppt_structure(request_data)

# ===== 5. 内容生成 Prompt（结构智能判断）=====

# 封面页生成函数
def generate_cover_content(page_data: dict, full_outline: dict, request_data, llm) -> str:
    """使用LLM根据整个PPT大纲生成封面页内容
    
    Args:
        page_data: 封面页的数据
        full_outline: 完整的PPT结构数据
        request_data: 用户请求数据
        llm: 语言模型实例
        
    Returns:
        str: 生成的封面页Markdown内容
    """
    # 首先构建完整大纲信息
    complete_outline = ""
    for section in full_outline['sections']:
        complete_outline += f"\nSection: {section['section']}\n"
        for page in section['pages']:
            if page['page'] > 1:  # Skip the cover page itself
                complete_outline += f"  - Page {page['page']}: {page['title']} - {page['summary']}\n"
    
    # 使用静态方法类中的封面页生成 Prompt
    prompt = PPTPrompts.cover_page_prompt(request_data, complete_outline)
    
    # 创建HumanMessage并调用LLM
    cover_message = HumanMessage(content=prompt)
    cover_response = llm.invoke([cover_message])
    
    # 提取响应内容
    cover_content = cover_response.content
    
    # 如果响应包含代码块，提取其中的内容
    cover_content = extract_json_from_markdown(cover_content)
    
    return cover_content

# 目录页自动生成函数
def generate_toc_content(page_data: dict, full_outline: dict) -> str:
    """为目录页自动生成内容
    
    Args:
        page_data: 目录页的数据
        full_outline: 完整的PPT结构数据
        
    Returns:
        str: 生成的目录页Markdown内容
    """
    # 生成目录页内容
    toc_content = "<!-- layout: toc-list -->\n\n"
    
    # 添加标题
    toc_content += f"# {page_data['title']}\n\n"
    
    # 为每个分区生成目录项
    for section in full_outline['sections']:
        section_name = section['section']
        toc_content += f"## {section_name}\n\n"
        
        # 添加该分区的页面（跳过封面和目录页本身）
        for page in section['pages']:
            if page['page'] <= 2:  # 跳过封面和目录页
                continue
            toc_content += f"- {page['title']} ... {page['page']}\n"
        
        toc_content += "\n"
    
    return toc_content

# 检查页面是否为封面页
def is_cover_page(page_data: dict) -> bool:
    """检查页面是否为封面页
    
    Args:
        page_data: 页面数据
        
    Returns:
        bool: 是否为封面页
    """
    # 检查页码（通常封面页是第1页）
    if page_data['page'] == 1:
        return True
    
    # 检查标题关键词
    title_lower = page_data['title'].lower()
    cover_keywords = ['cover', '封面', 'title', '标题', 'front']
    for keyword in cover_keywords:
        if keyword in title_lower:
            return True
    
    return False

# 检查页面是否为目录页
def is_toc_page(page_data: dict) -> bool:
    """检查页面是否为目录页
    
    Args:
        page_data: 页面数据
        
    Returns:
        bool: 是否为目录页
    """
    # 检查页码（通常目录页是第2页）
    if page_data['page'] == 2:
        return True
    
    # 检查标题关键词
    title_lower = page_data['title'].lower()
    toc_keywords = ['content', '目录', 'agenda', 'outline', 'table of contents']
    for keyword in toc_keywords:
        if keyword in title_lower:
            return True
    
    return False

# 内容生成函数
def content_prompt_markdown_structured(summary_text: str, topic: str, page_num: int, section_name: str, style: str, full_outline: dict, words_per_page: int = 120) -> str:
    
    # 获取当前页面所属的section中的所有页面
    current_section_pages = []
    for section in full_outline['sections']:
        if section['section'] == section_name:
            current_section_pages = section['pages']
            break
    
    # 构建当前分区的上下文信息
    section_context = f"\n\nCurrent Section: {section_name}\n"
    for page in current_section_pages:
        if page['page'] < page_num:  # 只包含当前页面之前的页面
            section_context += f"- Page {page['page']}: {page['title']} - {page['summary']}\n"
    
    # 构建完整大纲的上下文信息
    outline_context = "\n\nFull PPT Outline (by sections):\n"
    for section in full_outline['sections']:
        outline_context += f"Section: {section['section']}\n"
        for page in section['pages']:
            outline_context += f"  - Page {page['page']}: {page['title']}\n"
    
    # 使用静态方法类中的内容生成 Prompt
    return PPTPrompts.content_generation_prompt(
        summary_text=summary_text,
        topic=topic,
        page_num=page_num,
        section_name=section_name,
        style=style,
        section_context=section_context,
        outline_context=outline_context,
        words_per_page=words_per_page
    )

# 页面内容生成函数
def generate_page_content(page_data, structure_data, request_data, llm, verbose=True):
    """根据页面类型生成相应的内容
    
    Args:
        page_data: 页面数据
        structure_data: 完整的PPT结构数据
        request_data: 用户请求数据
        llm: 语言模型实例
        verbose: 是否打印详细信息
        
    Returns:
        str: 生成的页面内容
    """
    # 检查页面类型并分别处理
    if is_cover_page(page_data):
        # 如果是封面页，使用特殊处理
        if verbose:
            print(f"\n📖 检测到封面页: {page_data['title']} (第{page_data['page']}页)")
            print("\n📝 基于完整大纲生成封面内容\n")
        
        # 使用LLM生成封面内容，基于整个PPT大纲
        content_result = generate_cover_content(page_data, structure_data, request_data, llm)
        
    elif is_toc_page(page_data):
        # 如果是目录页，使用特殊处理
        if verbose:
            print(f"\n📗 检测到目录页: {page_data['title']} (第{page_data['page']}页)")
            print("\n📝 自动生成目录内容\n")
        
        # 跳过LLM调用，直接使用生成的目录内容
        content_result = generate_toc_content(page_data, structure_data)
        
    else:
        # 如果是普通内容页，使用正常的内容生成流程
        if verbose:
            print(f"\n📘 处理普通内容页: {page_data['title']} (第{page_data['page']}页)")
        
        # 生成内容提示
        content_prompt = content_prompt_markdown_structured(
            summary_text=page_data["summary"],
            topic=page_data["title"],
            page_num=page_data["page"],
            section_name=page_data["section"],  # 添加section信息
            style=request_data.style,
            full_outline=structure_data,  # 传入完整结构数据
            words_per_page=request_data.words_per_page or 120
        )

        # 创建HumanMessage并调用LLM
        content_message = HumanMessage(content=content_prompt)
        content_response = llm.invoke([content_message])

        # 清理响应内容，处理可能的markdown代码块
        content_result = extract_json_from_markdown(content_response.content)
    
    return content_result

# ===== 6. 内容生成调用（示例）=====
# 选择要生成内容的页面（这里选择第一页，封面页）
selected_page_index = 0  # 索引从0开始，所以这是第1页
selected_page = structure_data['pages'][selected_page_index]

# 调用函数生成页面内容
content_result = generate_page_content(selected_page, structure_data, request_data, llm)

# 如果想测试其他页面，可以取消下面的注释并选择不同页面
# selected_page_index = 1  # 选择第2页（目录页）
# selected_page = structure_data['pages'][selected_page_index]
# content_result = generate_page_content(selected_page, structure_data, request_data, llm)

# selected_page_index = 2  # 选择第3页（内容页）
# selected_page = structure_data['pages'][selected_page_index]
# content_result = generate_page_content(selected_page, structure_data, request_data, llm)

# ===== 7. 打印输出结构与内容 =====
# 打印选定页面的信息
print(f"📘 结构大纲（第{selected_page['page']}页，属于 '{selected_page['section']}' 分区）：\n", 
      json.dumps(selected_page, ensure_ascii=False, indent=2))

# 打印完整的分区结构（可选）
print("\n📗 完整PPT结构（分区数）：", len(structure_data['sections']))
for i, section in enumerate(structure_data['sections']):
    print(f"  - 分区 {i+1}: {section['section']} (包含{len(section['pages'])}页)")

# 打印生成的内容
print("\n📝 内容输出（结构化 Markdown）：\n", content_result)
