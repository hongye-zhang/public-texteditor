from typing import Dict, Any, Optional, AsyncGenerator, List
import asyncio
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import os
from app.models.editor_actions import create_insert_text_action

# Import PPTGenerator
from app.impls.PPTGenerator import PPTGenerator

# Get API key
api_key = os.getenv("OPENAI_API_KEY")

async def stream_ppt_generation(
    user_message: str,
    editor_content: Optional[str] = None,
    file_path: Optional[str] = None,
    create_new_intent = None,
    model: str = "gpt-4o",
    temperature: float = 0.7
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Streaming response function specifically for handling PPT generation requests
    
    Args:
        user_message: User message
        editor_content: Editor content (optional)
        file_path: Optional path to an uploaded file
        create_new_intent: Optional CreateNewIntent object with detailed intent information
        model: Model name to use
        temperature: Temperature parameter
        
    Returns:
        Async generator that produces streaming response events
    """
    try:
        # Create async queue for real-time token processing
        token_queue = asyncio.Queue()
        
        # Send "thinking" message
        yield {"type": "thinking", "content": "Analyzing your PPT request..."}
        
        # Initialize PPT Generator with the specified model, temperature, file path and create_new_intent
        ppt_generator = PPTGenerator(model=model, temperature=temperature, file_path=file_path, create_new_intent=create_new_intent)
        
        # If there's an uploaded file, notify the user
        if file_path:
            yield {"type": "thinking", "content": f"Processing uploaded file: {os.path.basename(file_path)}..."}
        
        # Step 1: Extract structure information
        yield {"type": "thinking", "content": "Extracting PPT structure information from your request..."}
        request_data = await asyncio.to_thread(ppt_generator.extract_ppt_structure, user_message, model, temperature)
        
        # Step 2: Generate PPT structure with sections
        yield {"type": "thinking", "content": "Generating PPT structure with logical sections..."}
        structure_data = await asyncio.to_thread(ppt_generator.generate_ppt_structure, request_data, model, temperature)
        
        # Log structure information for debugging
        section_info = ", ".join([f"{section['section']} ({len(section['pages'])} pages)" for section in structure_data['sections']])
        yield {"type": "thinking", "content": f"Created PPT structure with sections: {section_info}"}
        
        # Step 3: Generate content for each page by section
        yield {"type": "thinking", "content": "Generating content section by section..."}
        
        # Store the generator state
        ppt_generator.request_data = request_data
        ppt_generator.structure_data = structure_data
        
        # Create LLM instance
        llm = ChatOpenAI(model=model, temperature=temperature)
        
        # Process pages in sequence, grouped by section
        pages_content = {}
        total_pages = len(structure_data['pages'])
        total_sections = len(structure_data['sections'])
        
        # Group pages by section
        pages_by_section = {}
        for page in structure_data['pages']:
            section = page['section']
            if section not in pages_by_section:
                pages_by_section[section] = []
            pages_by_section[section].append(page)
        
        # Special handling for cover and TOC pages (usually in the first section)
        first_section = structure_data['sections'][0]['section']
        special_pages = []
        regular_section_pages = []
        
        if first_section in pages_by_section:
            for page in pages_by_section[first_section]:
                if ppt_generator.is_cover_page(page) or ppt_generator.is_toc_page(page):
                    special_pages.append(page)
                else:
                    regular_section_pages.append(page)
            
            # Replace the first section's pages with only regular pages
            if regular_section_pages:
                pages_by_section[first_section] = regular_section_pages
            else:
                # If all pages in the first section are special, remove the section
                del pages_by_section[first_section]
        
        # First process special pages (cover and TOC)
        section_content = []
        for i, page in enumerate(special_pages):
            # Determine page type for more specific progress messages
            if ppt_generator.is_cover_page(page):
                yield {"type": "thinking", "content": f"Creating cover page..."}
            elif ppt_generator.is_toc_page(page):
                yield {"type": "thinking", "content": f"Generating table of contents..."}
            
            # Generate content for this page
            content = await asyncio.to_thread(
                ppt_generator.generate_page_content,
                page_data=page,
                structure_data=structure_data,
                request_data=request_data,
                llm=llm,
                verbose=False  # Don't print verbose output in the server
            )
            
            # Store the content
            pages_content[page['page']] = {
                'title': page['title'],
                'section': page['section'],
                'content': content
            }
            
            # Add to section content for immediate return
            section_content.append({
                'page': page['page'],
                'title': page['title'],
                'section': page['section'],
                'content': content
            })
        
        # If we have special pages, return them immediately
        if section_content:
            # Create a partial markdown representation
            partial_markdown = []
            
            # Add a title for the entire PPT
            # partial_markdown.append(f"# {request_data.topic}\n")
            
            # Add each page's content
            for page_data in sorted(section_content, key=lambda x: x['page']):
                page_num = page_data['page']
                
                # Skip adding extra heading for cover page since it already has a title
                if page_num != 1:  # Not the cover page
                    # Add section information as a comment
                    # partial_markdown.append(f"<!-- Section: {page_data['section']} -->\n")
                    
                    # Add page title as a heading
                    #partial_markdown.append(f"## {page_data['title']}\n")
                    # the content has agenda in it
                    pass
                
                # Add the page content
                partial_markdown.append(f"{page_data['content']}\n")
                
                # Add a separator between pages
                partial_markdown.append("---\n")
            
            # Join all content
            partial_content = "\n".join(partial_markdown)

            # remove duplicate '---\n'
            partial_content = partial_content.replace("---\n---\n", "---\n")
            
            # Send action instruction for the special pages
            action = create_insert_text_action(content=partial_content, position="end", partial=True)
            yield {"type": "action", "content": "Cover and table of contents inserted into the editor.", "action": action}
        
        # Now process each section
        current_section = 0
        for section_name, section_pages in pages_by_section.items():
            current_section += 1
            section_content = []
            
            yield {"type": "thinking", "content": f"Generating Section {current_section}/{len(pages_by_section)}: {section_name}..."}
            
            for page in section_pages:
                page_index = structure_data['pages'].index(page)
                yield {"type": "thinking", "content": f"Developing content for page {page_index+1}/{total_pages}: {page['title']}..."}
                
                # Generate content for this page
                content = await asyncio.to_thread(
                    ppt_generator.generate_page_content,
                    page_data=page,
                    structure_data=structure_data,
                    request_data=request_data,
                    llm=llm,
                    verbose=False  # Don't print verbose output in the server
                )
                
                # Store the content
                pages_content[page['page']] = {
                    'title': page['title'],
                    'section': page['section'],
                    'content': content
                }
                
                # Add to section content for immediate return
                section_content.append({
                    'page': page['page'],
                    'title': page['title'],
                    'section': page['section'],
                    'content': content
                })
            
            # Create a partial markdown representation for this section
            partial_markdown = []
            
            # Add section heading once at the beginning with emoji
            partial_markdown.append(f"<!-- Section: {section_name} -->\n")
            
            # Add emoji based on section name
            emoji = "📊"  # Default emoji
            
            # Choose emoji based on section name (case insensitive)
            section_lower = section_name.lower()
            if "introduction" in section_lower or "overview" in section_lower:
                emoji = "🔍"
            elif "background" in section_lower or "history" in section_lower:
                emoji = "📜"
            elif "method" in section_lower or "approach" in section_lower:
                emoji = "🛠️"
            elif "result" in section_lower or "finding" in section_lower:
                emoji = "📈"
            elif "conclusion" in section_lower or "summary" in section_lower:
                emoji = "🎯"
            elif "recommendation" in section_lower or "next" in section_lower:
                emoji = "🚀"
            elif "case" in section_lower or "example" in section_lower:
                emoji = "💼"
            elif "challenge" in section_lower or "problem" in section_lower:
                emoji = "⚠️"
            elif "solution" in section_lower or "strategy" in section_lower:
                emoji = "💡"
            
            partial_markdown.append(f"## {emoji} {section_name}\n\n")
            
            # Add a separator after section
            partial_markdown.append("---\n")
            
            # Add each page's content
            for page_data in sorted(section_content, key=lambda x: x['page']):
                # Add page title as a heading
                partial_markdown.append(f"### {page_data['title']}\n")
                
                # Add the page content
                partial_markdown.append(f"{page_data['content']}\n")
                
                # Add a separator between pages
                partial_markdown.append("---\n")
            
            # Join all content
            partial_content = "\n".join(partial_markdown)
            
            # Send action instruction for this section
            action = create_insert_text_action(content=partial_content, position="end", partial=True)
            yield {"type": "action", "content": f"Section {current_section}/{len(pages_by_section)}: {section_name} inserted into the editor.", "action": action}
        
        # Step 4: Send completion message
        yield {"type": "thinking", "content": "PPT generation completed!"}
        
        # Send final completion message
        yield {"type": "message", "content": "PPT has been generated and inserted into the editor section by section."}
        
    except Exception as e:
        yield {"type": "error", "content": f"Error in PPT generation: {str(e)}"}
