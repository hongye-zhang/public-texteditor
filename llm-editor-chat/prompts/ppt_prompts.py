"""
PPT generation prompts module.
Contains static method classes for various PPT generation prompts.
"""

class PPTPrompts:
    """
    Static method class containing prompts for PPT generation.
    """
    
    @staticmethod
    def structure_extraction_prompt():
        """
        Returns the prompt for extracting structure information from user input.
        
        Returns:
            str: The structure extraction prompt
        """
        return """
You are a professional PPT writing planning assistant. Your task is to extract the key information needed to generate a PPT from the user's natural language input. The structure you need to output includes:

- topic: The topic of the PPT (e.g., Applications of AI in Education)
- use: The usage scenario of the PPT (e.g., internal company training, product launch event)
- pages: The number of pages expected by the user, must be an integer
- style: The overall style and tone (e.g., easy to understand, formal and professional, light and fun)
- structure_notes: The user's initial ideas about the PPT structure (can be an incomplete outline, logical sequence, content direction, etc.)
- words_per_page: The word limit per page, can be omitted if not specified

You will output a structured JSON object for subsequent generation of the PPT structure and content. Do not generate any extra explanations or descriptions.

If the user's input is incomplete, you can reasonably infer and fill in the gaps based on the context (e.g., interpret "a dozen pages" as 15).
"""
    
    @staticmethod
    def structure_prompt(request_data):
        """
        Returns the prompt for generating PPT structure outline.
        
        Args:
            request_data: The user request data containing topic, pages, use, style, and structure_notes
            
        Returns:
            str: The structure prompt with the request data filled in
        """
        return f"""
You are a professional PPT structure planning expert. Please generate a structural outline for a PPT with the topic "{request_data.topic}".

📌 Requirements:
- Organize the PPT into logical sections (e.g., Introduction, Background, Applications, Future)
- Plan approximately {request_data.pages} pages in total.
- Structure the output as follows:
    - section: The section name (e.g., "Introduction", "Background", etc.)
    - pages: An array of pages in this section, where each page includes:
        - page: Page number (numeric, sequential across the entire presentation)
        - title: Page title
        - summary: A 1-2 sentence description of the main content intended for the page, which can be expressed in Markdown format.
- Usage scenario: {request_data.use if request_data.use.lower() != "None" else "Not specified, please assume a general scenario"}
- Style preference: {request_data.style if request_data.style.lower() != "None" else "Not specified, please use a standard formal style"}
- The user's initial ideas about the structure are as follows (can be used as a reference, but not strictly adhered to):
{request_data.structure_notes or "None"}

📌 Output format requirements:
- Output a JSON array, where each element represents a section with its pages.
- Each section should have a "section" field (string) and a "pages" field (array).
- Each page in the "pages" array should include "page" (number), "title" (string), and "summary" (string).
- The summary can use Markdown, such as **emphasized words**, `terms`, - bullet lists, etc.
- Do not output the main content or bullet points, only plan the structure.
- Ensure page numbers are sequential across the entire presentation.

Example format:
```json
[
  {{
    "section": "Introduction",
    "pages": [
      {{"page": 1, "title": "Cover", "summary": "Title and presenter information"}},
      {{"page": 2, "title": "Agenda", "summary": "Overview of presentation topics"}}
    ]
  }},
  {{
    "section": "Background",
    "pages": [
      {{"page": 3, "title": "Context", "summary": "Industry background and **key challenges**"}}
    ]
  }}
]
```

Please start generating the structural outline for the PPT on {request_data.topic}.
"""
        
    @staticmethod
    def cover_page_prompt(request_data, complete_outline):
        """
        Returns the prompt for generating a cover page based on the PPT outline.
        
        Args:
            request_data: The user request data containing topic, use, and style
            complete_outline: A string containing the formatted outline of the PPT
            
        Returns:
            str: The cover page generation prompt with the request data and outline filled in
        """
        return f"""
You are a professional PPT cover design expert. Based on the following complete PPT outline, please generate an eye-catching, professional, and accurate cover page content.

📌 PPT Topic: {request_data.topic}
📌 Usage Scenario: {request_data.use}
📌 Style Preference: {request_data.style}

📌 Complete PPT Outline:
{complete_outline}

📌 Output Requirements:
1. Generate an eye-catching main title that accurately reflects the core theme of the entire PPT
2. Generate a concise subtitle that complements the main title or provides additional information
3. Add other cover elements such as author, date, etc.
4. Use Markdown format and include the layout tag <!-- layout: cover --> on the first line

Please output the cover page Markdown content directly without adding explanations or other content.
"""
    
    @staticmethod
    def content_generation_prompt(summary_text, topic, page_num, section_name, style, section_context, outline_context, words_per_page):
        """
        Returns the prompt for generating structured content for a PPT page.
        
        Args:
            summary_text: The summary of the page content
            topic: The topic of the page
            page_num: The page number
            section_name: The name of the section this page belongs to
            style: The style preference for the content
            section_context: Context information about the current section
            outline_context: Context information about the full PPT outline
            words_per_page: The word limit per page
            
        Returns:
            str: The content generation prompt with all parameters filled in
        """
        return f"""
You are a professional PPT content organization expert. Based on the page summary content and the overall PPT outline, determine the most suitable content structure and output it in structured Markdown format.

You are currently working on Page {page_num}: {topic} in the "{section_name}" section.

📔 Page Topic (Page {page_num}):
{topic}

📝 Page Summary:
{summary_text}
{section_context}
{outline_context}

🎨 Style Requirements:
- Content style: {style if style.lower() != "none" else "standard formal style"}
- Use concise and clear language, avoid long paragraphs
- Total word count should be limited to {words_per_page} words (excluding Markdown syntax)

---

🎡 You can choose from the following content organization methods. Please automatically select the most appropriate one based on the content:

- `smartart-list`: List type (e.g., "3 main advantages," "4 dimensions"), using "**Keyword**: one sentence explanation" format, with unified bullet structure.
- `smartart-hierarchy`: Hierarchical type (e.g., "3 main directions, each with 2 sub-points"), must have a consistent two-level bullet structure.
- `smartart-process`: Process type (e.g., "Step 1 → Step 2 → Step 3"), suitable for step descriptions or development evolution.
- `table`: Table type, suitable for comparing multiple entities across multiple dimensions (output using Markdown tables).
- `plain-bullet`: Plain bullet list, use this if a clear structure cannot be determined.

---

🛠 Output Requirements:

- The first line must include a layout tag, such as: `<!-- layout: smartart-list -->`
- Then output Markdown content, with neat formatting and clear structure
- Use appropriate bullets, tables, or nested structures to present the content
- Do not output any explanatory text, do not write "Here is the content" or "We can see"

Please start generating structured Markdown for this page's content.
""".strip()
    
    @staticmethod
    def format_instructions():
        """
        Returns the format instructions for the structure extraction prompt.
        
        Returns:
            str: The format instructions
        """
        return """
Please output in JSON format with the following fields:
- topic: string, the main topic of the PPT
- use: string, the purpose or usage scenario of the PPT
- pages: integer, the number of pages in the PPT
- style: string, the style or tone of the PPT
- structure_notes: string, notes about the structure (optional)
- words_per_page: integer, number of words per page (optional)

For example:
{"topic": "Applications of AI in Education", "use": "Internal presentation", "pages": 15, "style": "Easy to understand", "structure_notes": "Background, Trends, Scenarios, Future", "words_per_page": 100}
"""
