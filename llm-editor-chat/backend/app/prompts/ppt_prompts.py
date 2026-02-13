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
- language: The language of the input text (e.g., English, Chinese, etc.)
- use: The usage scenario of the PPT (e.g., internal company training, product launch event)
- pages: The number of pages expected by the user, must be an integer
- style: The overall style and tone (e.g., easy to understand, formal and professional, light and fun)
- structure_notes: The user's initial ideas about the PPT structure (can be an incomplete outline, logical sequence, content direction, etc.)
- words_per_page: The word limit per page, can be omitted if not specified

You will output a structured JSON object for subsequent generation of the PPT structure and content. Do not generate any extra explanations or descriptions.

If the user's input is incomplete, you can reasonably infer and fill in the gaps based on the context (e.g., interpret "a dozen pages" as 15).
"""
    
    @staticmethod
    def structure_prompt(request_data, has_reference_file=False):
        """
        Returns the prompt for generating PPT structure outline.
        
        Args:
            request_data: The user request data containing topic, pages, use, style, and structure_notes
            has_reference_file: Boolean indicating whether a reference file is provided
            
        Returns:
            str: The structure prompt with the request data filled in
        """
        # Determine if PPT should be based on file content
        is_content_based = False
        if hasattr(request_data, 'use') and request_data.use:
            is_content_based = ("based on the uploaded file content" in request_data.use.lower() or 
                               "content_based" in request_data.use.lower())
        
        # Get style preference formatted for prompt
        style_preference = (request_data.style 
                           if request_data.style.lower() != "None" 
                           else "Not specified, please use a standard formal style")
        
        # Get language preference formatted for prompt
        language_preference = (request_data.language 
                              if getattr(request_data, 'language', None) and request_data.language.lower() != 'none' 
                              else 'English')
        
        # Get structure notes formatted for prompt
        structure_notes = request_data.structure_notes or "None"
        
        # Generate base prompt based on file usage intent
        if is_content_based and has_reference_file:
            # Content-based prompt (when file is the primary source)
            base_prompt = f"""
You are a professional PPT structure planning expert. Please generate a structural outline for a PPT that is PRIMARILY BASED ON THE UPLOADED FILE CONTENT, with "{request_data.topic}" as a guiding theme.

REQUIREMENTS:
- IMPORTANT: The structure should be derived primarily from the content of the uploaded file, not from general knowledge about the topic.
- Extract key sections, concepts, and information from the file to form the main structure of the presentation.
- Organize the extracted content into logical sections (e.g., Introduction, Main Content, Conclusion)
- Use 4-6 main sections in total (including Cover) to avoid excessive fragmentation
- Combine related topics into cohesive sections rather than creating many small sections
- Distribute content evenly, with more pages allocated to core content sections
- **IMPORTANT**: Plan approximately {request_data.pages} slides/pages in total (NOT including section headers). The final count should be within 10-15% of this target.
- Structure the output as follows:
    - section: The section name (e.g., "Introduction", "Background", etc.)
    - pages: An array of pages in this section, where each page includes:
        - page: Page number (numeric, sequential across the entire presentation)
        - title: Page title
        - summary: A 1-2 sentence description of the main content intended for the page, which can be expressed in Markdown format.
- Usage scenario: Creating a presentation primarily based on the uploaded file content
- Style preference: {style_preference}
- Output language: {language_preference}
- The user's initial ideas about the structure are as follows (can be used as a reference, but not strictly adhered to):
{structure_notes}
"""
        else:
            # Topic-based prompt (when file is reference only or no file)
            usage_scenario = (request_data.use 
                             if request_data.use.lower() != "None" 
                             else "Not specified, please assume a general scenario")
            
            base_prompt = f"""
You are a professional PPT structure planning expert. Please generate a structural outline for a PPT with the topic "{request_data.topic}".

REQUIREMENTS:
- Organize the PPT into logical sections (e.g., Introduction, Main Content, Conclusion)
- Use 4-6 main sections in total (including Cover) to avoid excessive fragmentation
- Combine related topics into cohesive sections rather than creating many small sections
- Distribute content evenly, with more pages allocated to core content sections
- **IMPORTANT**: Plan approximately {request_data.pages} slides/pages in total (NOT including section headers). The final count should be within 10-15% of this target.
- Structure the output as follows:
    - section: The section name (e.g., "Introduction", "Background", etc.)
    - pages: An array of pages in this section, where each page includes:
        - page: Page number (numeric, sequential across the entire presentation)
        - title: Page title
        - summary: A 1-2 sentence description of the main content intended for the page, which can be expressed in Markdown format.
- Usage scenario: {usage_scenario}
- Style preference: {style_preference}
- Output language: {language_preference}
- The user's initial ideas about the structure are as follows (can be used as a reference, but not strictly adhered to):
{structure_notes}
"""

        # Add output format requirements to both prompt types
        output_format = f"""
OUTPUT FORMAT REQUIREMENTS:
- Output a JSON array, where each element represents a section with its pages.
- The first element MUST be a special section with "section": "Cover" containing exactly two pages:
  - Page 1: Cover page with title and presenter information
  - Page 2: Agenda/Table of Contents page
- **IMPORTANT VALIDATION STEPS** before finalizing your output:
  1. Count the total number of individual pages across all sections (including the Cover section). This total should be approximately {request_data.pages} pages (within 10-15% of this target)
  2. Check that you have no more than 6 total sections to avoid excessive fragmentation
  3. Verify that core content sections have proportionally more pages than introductory or concluding sections
  4. Ensure related topics are grouped together rather than split across multiple sections
- All subsequent elements represent content sections (Introduction, Background, etc.)
- Each section should have a "section" field (string) and a "pages" field (array).
- Each page in the "pages" array should include "page" (number), "title" (string), and "summary" (string).
- The summary can use Markdown, such as **emphasized words**, `terms`, - bullet lists, etc.
- Do not output the main content or bullet points, only plan the structure.
- Ensure page numbers are sequential across the entire presentation.

Example format (for a presentation with approximately 8 pages):
```json
[
  {{
    "section": "Cover",
    "pages": [
      {{"page": 1, "title": "Cover", "summary": "Title and presenter information"}},
      {{"page": 2, "title": "Agenda", "summary": "Overview of presentation topics"}}
    ]
  }},
  {{
    "section": "Introduction",
    "pages": [
      {{"page": 3, "title": "Project Overview", "summary": "Introduction to the project scope and goals"}}
    ]
  }},
  {{
    "section": "Main Content",
    "pages": [
      {{"page": 4, "title": "Key Features", "summary": "Three primary features of the system"}},
      {{"page": 5, "title": "Technical Details", "summary": "Implementation details and architecture"}},
      {{"page": 6, "title": "Benefits", "summary": "Main advantages and business value"}}
    ]
  }},
  {{
    "section": "Conclusion",
    "pages": [
      {{"page": 7, "title": "Summary", "summary": "Recap of key points and main takeaways"}},
      {{"page": 8, "title": "Next Steps", "summary": "Action items and future directions"}}
    ]
  }}
]
```

NOTE: The above is just an example format. Your actual output should have approximately {request_data.pages} total pages distributed appropriately across sections based on the topic.

Please start generating the structural outline for the PPT on {request_data.topic}.
"""
        
        # Combine base prompt with output format
        complete_prompt = base_prompt + output_format
        
        # Add reference file instructions if applicable
        if has_reference_file:
            # Different reference prompts based on file usage intent
            if is_content_based:
                # Content-based reference prompt (when file is the primary source)
                reference_prompt = f"""

REFERENCE DOCUMENT:
A reference document (PDF) has been provided. This document should be the PRIMARY SOURCE for your PPT structure. Please analyze it thoroughly and:

1. Extract the main topics, key points, and logical flow from the document
2. Use these extracted elements as the foundation for your PPT structure
3. Organize the document's content into a coherent presentation structure
4. Ensure all important information from the document is represented in the structure

IMPORTANT: The document's content should drive the structure of the presentation, with "{request_data.topic}" as the guiding theme. Your task is to transform the document into a well-structured presentation, not to create a presentation about the topic using general knowledge.
"""
            else:
                # Reference-only prompt (when file is supplementary)
                reference_prompt = f"""

REFERENCE DOCUMENT:
A reference document (PDF) has been provided. Please use this document as a SUPPLEMENTARY REFERENCE while creating a presentation structure for the topic "{request_data.topic}". Your approach should be to:

1. First, develop a logical structure for the presentation based on the topic
2. Then, incorporate relevant information from the reference document where appropriate
3. Use the document to enhance specific sections with supporting data, examples, or concepts
4. Maintain focus on the requested topic, using the document as a resource rather than the primary content source

IMPORTANT: The presentation structure should primarily follow the topic "{request_data.topic}", with the document serving as a valuable reference to enrich the content.
"""
            
            complete_prompt += reference_prompt
            
        return complete_prompt
        
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
📌 Output language: {request_data.language if getattr(request_data, 'language', None) and request_data.language.lower() != 'none' else 'English'}

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
    def content_generation_prompt(summary_text, topic, page_num, section_name, style, section_context, outline_context, words_per_page, language=None, has_reference_file=False):
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
            language: The language of the content
            has_reference_file: Boolean indicating whether a reference file is provided
            
        Returns:
            str: The content generation prompt with all parameters filled in
        """
        # 基本提示词模板
        base_prompt = f"""
You are a professional PPT content organization expert. Based on the page summary content and the overall PPT outline, determine the most suitable content structure and output it in structured Markdown format.

You are currently working on Page {page_num}: {topic} in the "{section_name}" section.

PAGE TOPIC (Page {page_num}):
{topic}

PAGE SUMMARY:
{summary_text}
{section_context}
{outline_context}

STYLE REQUIREMENTS:
- Content style: {style if style.lower() != "none" else "standard formal style"}
- Output language: {language if language and language.lower() != 'none' else 'English'}
- Use concise and clear language, avoid long paragraphs
- Total word count should be limited to {words_per_page} words (excluding Markdown syntax)

---

CONTENT ORGANIZATION METHODS:
Please automatically select the most appropriate organization method based on the content:

- `smartart-list`: List type (e.g., "3 main advantages," "4 dimensions"), using "**Keyword**: one sentence explanation" format, with unified bullet structure.
- `smartart-hierarchy`: Hierarchical type (e.g., "3 main directions, each with 2 sub-points"), must have a consistent two-level bullet structure.
- `smartart-process`: Process type (e.g., "Step 1 → Step 2 → Step 3"), suitable for step descriptions or development evolution.
- `table`: Table type, suitable for comparing multiple entities across multiple dimensions (output using Markdown tables).
- `plain-bullet`: Plain bullet list, use this if a clear structure cannot be determined.

---

OUTPUT REQUIREMENTS:

- The first line must include a layout tag, such as: `<!-- layout: smartart-list -->`
- Then output Markdown content, with neat formatting and clear structure
- Use appropriate bullets, tables, or nested structures to present the content
- Do not output any explanatory text, do not write "Here is the content" or "We can see"
"""
        
        # 如果有参考文件，添加相关指示
        if has_reference_file:
            reference_prompt = f"""

REFERENCE DOCUMENT INSTRUCTIONS:
A PDF reference document has been provided. Please analyze this document carefully and use its content to inform your page content generation. Extract relevant information, key points, and data from the document that relates to the current page topic.

Important: 
- Your content should be based on the reference document while addressing the page topic "{topic}".
- Extract and incorporate specific facts, statistics, quotes, or examples from the document when relevant.
- Maintain consistency with the overall PPT structure and style.
- Do not simply copy text from the document - synthesize and organize the information appropriately for a presentation slide.
"""
            return (base_prompt + reference_prompt + "\n\nPlease start generating structured Markdown for this page's content.").strip()
        else:
            return (base_prompt + "\n\nPlease start generating structured Markdown for this page's content.").strip()
    
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
- language: string, the language of the input text
- use: string, the purpose or usage scenario of the PPT
- pages: integer, the number of pages in the PPT
- style: string, the style or tone of the PPT
- structure_notes: string, notes about the structure (optional)
- words_per_page: integer, number of words per page (optional)

For example:
{"topic": "Applications of AI in Education", "language": "English", "use": "Internal presentation", "pages": 15, "style": "Easy to understand", "structure_notes": "Background, Trends, Scenarios, Future", "words_per_page": 100}
"""
