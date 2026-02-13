from typing import Dict, Any, Optional, List, Set, Union
from app.features.document_structure.services.document_analyzer import DocumentStructureAnalyzer  # Updated import path
from app.features.document_structure.services.section_finder import SectionFinder  # Updated import path
from app.features.document_editing.services.prompt_generator import generate_edit_prompt  # Updated import path
from app.features.document_editing.services.section_editor import SectionEditor  # Updated import path
import json
import traceback
import random

# API key for OpenAI

class DocumentPipeline:
    def __init__(self, api_key: str):
        """Initialize the document analysis pipeline with OpenAI API key."""
        self.api_key = api_key
        self.document_analyzer = DocumentStructureAnalyzer(api_key)
        self.section_finder = SectionFinder(api_key)
        self.section_editor = SectionEditor(api_key)
        
    def analyze_document(self, markdown_text: str, docx_path: Optional[str] = None) -> Dict[str, Any]:
        """Analyze document structure and return complete analysis.
        
        Args:
            markdown_text: The markdown text to analyze
            docx_path: Optional path to docx file
            
        Returns:
            Dict containing document structure and analysis
        """
        # Step 1: Analyze document structure
        doc_structure = self.document_analyzer.analyze_docx(markdown_text, docx_path)
        structure = self.document_analyzer.get_document_structure(doc_structure)
        
        return structure
    
    def find_relevant_sections(self, prompt: str, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Find sections relevant to the user's prompt.
        
        Args:
            prompt: The user's prompt
            structure: Document structure from analyze_document
            
        Returns:
            Dict containing main and supplementary sections
        """
        # Step 2: Find relevant sections
        sections = structure.get("sections", [])
        
        # Flatten the section structure to make it easier to process
        flattened_sections = self._flatten_sections(sections)
        
        print("\nDebug - Input Sections (flattened):")
        print(f"Found {len(flattened_sections)} sections after flattening")
        for i, section in enumerate(flattened_sections[:5]):  # Print first 5 for brevity
            print(f"Section {i}: {section.get('title')} (Lines: {section.get('start_line')}-{section.get('end_line')})")
        
        print("\nDebug - Prompt for section finding:")
        print(f"Prompt: {prompt}")
        
        result = self.section_finder.analyze_sections(prompt, flattened_sections)
        print("\nDebug - Section Finder Output:")
        print(json.dumps(result, indent=2))
        
        # Validate result structure
        if not isinstance(result, dict):
            raise ValueError("Section finder returned invalid result type")
        if "main" not in result:
            raise ValueError("Section finder result missing 'main' section")
        if "title" not in result["main"] or "lines" not in result["main"]:
            raise ValueError("Main section missing required fields")
            
        return result
    
    def _generate_random_hex_id(self, existing_ids: Optional[Set[str]] = None) -> str:
        """Generate a random 4-digit hexadecimal ID.
        
        Args:
            existing_ids: Set of already used IDs to ensure uniqueness
            
        Returns:
            str: A unique 4-digit hexadecimal ID
        """
        while True:
            new_id = f"{random.randint(0, 0xFFFF):04x}"
            if existing_ids is None or new_id not in existing_ids:
                return new_id

    def add_ids_to_nodes(self, node: Union[dict, list], node_id: str = None, 
                        existing_ids: Optional[Set[str]] = None) -> Union[dict, list]:
        """
        Recursively add unique random 4-digit hex IDs to all nodes in the JSON structure.
        
        Args:
            node: The current node to process (can be dict, list, or other types)
            node_id: Optional parent node ID for reference
            existing_ids: Set of already used IDs to ensure uniqueness
            
        Returns:
            The processed node with IDs added
        """
        if existing_ids is None:
            existing_ids = set()
            
        if isinstance(node, dict):
            # Add ID to the current node if it's an object (not a text node)
            if 'type' in node and not node.get('id'):
                # Generate a unique 4-digit hex ID
                new_id = self._generate_random_hex_id(existing_ids)
                node['id'] = new_id
                existing_ids.add(new_id)
            
            # Recursively process all values in the dictionary
            for key, value in node.items():
                node[key] = self.add_ids_to_nodes(value, node.get('id'), existing_ids)
                
        elif isinstance(node, list):
            # Process each item in the list
            for i, item in enumerate(node):
                node[i] = self.add_ids_to_nodes(item, node_id, existing_ids)
        
        return node

    def flatten_nodes_to_list(self, node: Union[dict, list], result: Optional[List[Dict[str, Any]]] = None, current_path: str = "", parent_idx: int = 0) -> List[Dict[str, Any]]:
        """
        Convert the hierarchical JSON structure into a flat list of nodes with IDs and text content.
        The order follows the natural reading order of the document.
        Only leaf nodes that represent actual visible content to humans are included.
        
        Args:
            node: The current node to process
            result: List to store the flattened nodes (used for recursion)
            current_path: Current path in the JSON structure (internal use for recursion)
            parent_idx: Index in parent array if node is part of an array (internal use for recursion)
            
        Returns:
            List of dictionaries with 'id' and 'text' keys
        """
        if result is None:
            result = []
        
        if isinstance(node, dict):
            # Build path for current node
            node_path = current_path
            
            # Get node ID - check both direct 'id' and 'attrs.id' paths
            node_id = None
            if 'id' in node:
                node_id = node['id']
            elif 'attrs' in node and isinstance(node['attrs'], dict) and 'id' in node['attrs']:
                node_id = node['attrs']['id']
            
            # Determine if this is a leaf node (actual content) or an intermediate container node
            is_leaf_node = False
            
            # Check if node has direct text content
            if 'text' in node and isinstance(node['text'], str) and node['text'].strip():
                is_leaf_node = True
            
            # Check if node has content array but no further nested content
            # (meaning it's a leaf paragraph or similar)
            elif 'content' in node and isinstance(node['content'], list):
                # Check if content items are mostly text or have their own nested content
                text_items = 0
                nested_content_items = 0
                
                for item in node['content']:
                    if isinstance(item, dict):
                        if 'text' in item and isinstance(item['text'], str) and item['text'].strip():
                            text_items += 1
                        if 'content' in item and isinstance(item['content'], list):
                            nested_content_items += 1
                
                # If node has mostly text items and few or no nested content items,
                # consider it a leaf node
                if text_items > 0 and nested_content_items == 0:
                    is_leaf_node = True
            
            # Only add leaf nodes with content to the result
            if is_leaf_node and node_id is not None:
                # For direct text content
                if 'text' in node and isinstance(node['text'], str):
                    result.append({
                        'id': node_id,
                        'text': node['text']
                    })
                # For content array
                elif 'content' in node and isinstance(node['content'], list):
                    text_content = self._extract_text_from_content(node['content'])
                    if text_content:
                        result.append({
                            'id': node_id,
                            'text': text_content
                        })
            # For non-leaf nodes, traverse their children/content
            else:
                # Process children if present
                if 'children' in node and isinstance(node['children'], list):
                    child_path = f"{node_path}.children" if node_path else "children"
                    for i, child in enumerate(node['children']):
                        self.flatten_nodes_to_list(child, result, f"{child_path}[{i}]", i)
                
                # Process content array
                if 'content' in node and isinstance(node['content'], list):
                    content_path = f"{node_path}.content" if node_path else "content"
                    for i, item in enumerate(node['content']):
                        self.flatten_nodes_to_list(item, result, f"{content_path}[{i}]", i)
                
                # Process other attributes that might contain nested structures
                for key, value in node.items():
                    if key not in ['id', 'text', 'children', 'content', 'attrs'] and (isinstance(value, dict) or isinstance(value, list)):
                        next_path = f"{node_path}.{key}" if node_path else key
                        self.flatten_nodes_to_list(value, result, next_path, 0)
        
        # Handle lists (like content arrays)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                item_path = f"{current_path}[{i}]" if current_path else f"[{i}]"
                self.flatten_nodes_to_list(item, result, item_path, i)
        
        return result

    def _extract_text_from_content(self, content: List[Dict[str, Any]]) -> str:
        """
        Extract text from content array in the new node format.
        
        Args:
            content: List of content items that may contain text
        
        Returns:
            Concatenated text from the content array
        """
        text_parts = []
        
        for item in content:
            if isinstance(item, dict):
                # Direct text in content item
                if 'text' in item and isinstance(item['text'], str):
                    text_parts.append(item['text'])
                # Recursive extraction from nested content
                elif 'content' in item and isinstance(item['content'], list):
                    nested_text = self._extract_text_from_content(item['content'])
                    if nested_text:
                        text_parts.append(nested_text)
    
        return ' '.join(text_parts)

    def _flatten_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten the hierarchical section structure.
        
        Args:
            sections: Hierarchical section structure
            
        Returns:
            Flattened list of sections
        """
        flattened = []
        
        def _flatten_recursive(section_list):
            for section in section_list:
                # Create a copy without the children
                section_copy = section.copy()
                if 'children' in section_copy:
                    # Process children recursively
                    _flatten_recursive(section_copy['children'])
                    # Remove children from the copy
                    del section_copy['children']
                # Add to flattened list if it has a title
                if 'title' in section_copy:
                    flattened.append(section_copy)
        
        _flatten_recursive(sections)
        return flattened

    def generate_edit_prompt(self, markdown_text: str, section_info: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """Generate a prompt for editing the selected section.
        
        Args:
            markdown_text: The full document text
            section_info: Section information from find_relevant_sections
            prompt: The user's prompt
            
        Returns:
            Dict containing the generated prompt and extracted sections
        """
        print("\nDebug - Section Info Input to generate_edit_prompt:")
        print(json.dumps(section_info, indent=2))
        
        try:
            # Validate section info
            if not isinstance(section_info, dict):
                raise ValueError("Invalid section info type")
            if "main" not in section_info:
                raise ValueError("Missing main section")
            if "title" not in section_info["main"] or "lines" not in section_info["main"]:
                raise ValueError("Main section missing required fields")
            
            # Convert section info to expected format for prompt_generator
            formatted_section_info = {
                "main_section": {
                    "title": section_info["main"]["title"],
                    "lines": section_info["main"]["lines"]
                },
                "supplementary_sections": []
            }
            
            # Add supplementary sections if they exist
            if "supplement" in section_info and isinstance(section_info["supplement"], list):
                formatted_section_info["supplementary_sections"] = [
                    {
                        "title": supp["title"],
                        "lines": supp["lines"],
                        "summary": supp.get("summary", "")
                    }
                    for supp in section_info["supplement"]
                    if isinstance(supp, dict) and "title" in supp and "lines" in supp
                ]
            
            print("\nDebug - Formatted Section Info:")
            print(json.dumps(formatted_section_info, indent=2))
            
            # Step 3: Generate edit prompt
            try:
                generated_prompt = generate_edit_prompt(markdown_text, formatted_section_info, prompt)
                return {
                    "generated_prompt": generated_prompt,
                    "sections_extracted": formatted_section_info
                }
            except Exception as e:
                print(f"Error generating edit prompt: {str(e)}")
                traceback.print_exc()
                raise ValueError(f"Failed to generate edit prompt: {str(e)}")
            
        except Exception as e:
            print(f"Error formatting section info: {str(e)}")
            traceback.print_exc()
            raise

    def apply_edit(self, file_path: str, prompt: Dict[str, Any]) -> None:
        """Apply the edit to the document.
        
        Args:
            file_path: Path to the file to edit
            prompt: The prompt generated by generate_edit_prompt
        """
        # Step 4: Get AI edit and apply it
        diff = self.section_editor.get_ai_edit(prompt)
        
        # Extract line numbers from section info
        main_section = prompt["sections_extracted"]["main_section"]
        lines = main_section["lines"]
        start_line, end_line = map(int, lines.split("-"))
        start_line -= 1  # Convert to 0-based indexing
        end_line -= 1
        
        # Apply the edit to the file
        self.section_editor.apply_to_file(file_path, diff, start_line, end_line)

    def process_document(self, file_path: str, prompt: str) -> None:
        """Process a document through the pipeline.
        
        Args:
            file_path: Path to the document to process
            prompt: The user's instruction for section selection and editing
        """
        try:
            # Step 1: Analyze document structure
            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
            
            # Ensure we have content to analyze
            if not markdown_text or markdown_text.strip() == "":
                print("Warning: Empty document content")
                raise ValueError("The document is empty")
                
            print(f"\nDebug - Document content length: {len(markdown_text)} characters")
            print(f"Debug - First 100 characters: {markdown_text[:100]}")
            
            print("\nDebug - Analyzing document structure...")
            structure = self.analyze_document(markdown_text)
            print(json.dumps(structure, indent=2))
            
            # Validate structure
            if structure["total_lines"] <= 1:
                print("Warning: Document has very few lines")
                
            # Step 2: Find relevant sections
            print("\nDebug - Finding relevant sections...")
            section_info = self.find_relevant_sections(prompt, structure)
            print("\nDebug - Section Info:")
            print(json.dumps(section_info, indent=2))
            
            # Step 3: Generate edit prompt
            print("\nDebug - Generating edit prompt...")
            edit_prompt = self.generate_edit_prompt(markdown_text, section_info, prompt)
            print("\nDebug - Generated Prompt:")
            print(json.dumps(edit_prompt, indent=2))
            
            # Step 4: Apply edit
            print("\nDebug - Applying edit...")
            self.apply_edit(file_path, edit_prompt)
            
        except Exception as e:
            print(f"Error in document pipeline: {str(e)}")
            traceback.print_exc()
            raise

    def dump_flattened_nodes(self, flattened: List[Dict[str, Any]]) -> str:
        """Convert flattened nodes into a formatted string for LLM processing.
        
        Args:
            flattened: List of node dictionaries with 'id' and 'text' keys
            
        Returns:
            Formatted string where each line represents a node with its ID and text
        """
        result = []
        for node in flattened:
            node_id = node.get('id', 'N/A')
            text = node.get('text', '')
            # Add ID and text, each node on a new line
            result.append(f"[ID:{node_id}] {text}")
        
        # Join all nodes with double newlines to separate paragraphs
        return "\n".join(result)

    def _parse_edited_content(self, edited_content: str, original_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse the edited content from LLM and create incremental JSON updates.
        
        Args:
            edited_content: The LLM-edited content with [ID:xxxx] markers
            original_nodes: The original flattened nodes list with paths
            
        Returns:
            List of path-based updates for the frontend, preserving the order from edited_content
        """
        # Create dictionaries for lookup
        original_nodes_by_id = {node['id']: node for node in original_nodes}
        
        # Split edited_content into paragraphs
        paragraphs = edited_content.split('\n')
        
        # Import necessary modules
        import re
        import uuid
        
        # Define ID pattern
        id_pattern = r'\[ID:?\s*([a-zA-Z0-9]+)\]'
        
        # Initialize lists for processing
        path_updates = []
        processed_ids = set()  # Track which IDs we've already processed
        
        # Process each paragraph
        for paragraph_text in paragraphs:
            current_paragraph_stripped = paragraph_text.strip()
            if not current_paragraph_stripped:
                continue

            is_new_node = False
            # Content after potentially stripping [NEW] tag
            content_after_new_tag_processing = current_paragraph_stripped

            if current_paragraph_stripped.startswith('[NEW]'):
                is_new_node = True
                content_after_new_tag_processing = current_paragraph_stripped.replace('[NEW]', '', 1).strip()

            id_match = re.search(id_pattern, content_after_new_tag_processing)
            
            parsed_node_id_from_tag = None
            # Content after potentially stripping [ID:...] from content_after_new_tag_processing
            final_text_content = content_after_new_tag_processing 

            if id_match:
                parsed_node_id_from_tag = id_match.group(1).strip()
                final_text_content = re.sub(id_pattern, '', content_after_new_tag_processing, 1).strip()

            if final_text_content == '(empty)':
                final_text_content = ''
        
            # Specific handling for [NEW] marked nodes
            if is_new_node:
                # Use parsed_node_id_from_tag if available, otherwise generate a new one.
                node_id_for_update = parsed_node_id_from_tag if parsed_node_id_from_tag else str(uuid.uuid4())[:4]

                # If an ID was explicitly provided with [NEW] (e.g., [NEW] [ID:new1]), and it was already processed, skip.
                if parsed_node_id_from_tag and parsed_node_id_from_tag in processed_ids:
                    continue
            
                path_updates.append({
                    'path': 'new',
                    'content': final_text_content,
                    'id': node_id_for_update
                })

                if parsed_node_id_from_tag:
                    processed_ids.add(parsed_node_id_from_tag)
        
            # Handling for existing nodes (not marked [NEW] but have an ID tag)
            else:
                if not parsed_node_id_from_tag: # Must have an ID if not a new node.
                    continue
            
                if parsed_node_id_from_tag in processed_ids: # Already processed this ID.
                    continue
            
                # This check prevents `[ID:xxxx]` (if it's the only thing left after another ID was stripped) from being treated as content for an existing node.
                if final_text_content.startswith('[ID:') and len(final_text_content) < 15: 
                    continue

                processed_ids.add(parsed_node_id_from_tag) # Mark as processed here for existing nodes.
            
                if parsed_node_id_from_tag in original_nodes_by_id:
                    original_node = original_nodes_by_id[parsed_node_id_from_tag]
                    original_text = original_node['text']
                    # Since we no longer store path in original_node, set node_path to None
                    node_path = None
                
                    if final_text_content != original_text:
                        path_updates.append({
                            'path': node_path,
                            'content': final_text_content,
                            'id': parsed_node_id_from_tag
                        })
                # else: ID found, but not in original_nodes and not marked [NEW]. 
                # This implies an edit instruction for a non-existent node that wasn't explicitly marked as new.
                # Current logic correctly ignores it by not adding to path_updates.    })
        
        return path_updates
    
    async def process_jsonnode(self, jsonnode: Dict[str, Any], message: str, selected_text: str, selected_nodes_ids: List[str], chat_history: Optional[List[Dict[str, str]]] = []) -> Dict[str, Any]:
        """Process a JSON node through the pipeline"""
        # we add id of node in frontend
        flattened = self.flatten_nodes_to_list(jsonnode)
        dumpstr = self.dump_flattened_nodes(flattened)

        # 按照selected_nodes_ids过滤flattened，得到新的列表 flattened_selected
        flattened_selected = [node for node in flattened if node['id'] in selected_nodes_ids]
        selected_paragraphs = self.dump_flattened_nodes(flattened_selected)
        
        # 从modify_prompts.py中读取system_prompt
        from app.prompts.modify_prompts import ModifyPrompts
        system_prompt = ModifyPrompts.modify_prompt_system()
        
        # 调用LLM完成编辑
        try:
            # 导入LLM工具函数
            from app.utils.llm_utils import generate_text
            
            # 构建用户提示
            user_prompt_template = """You will edit the [Document Content] according to the [User Instructions]. Each paragraph in the document content has a unique ID.
            The user has explicitly selected certain paragraphs. These [Selected Paragraphs] represent the user's "area of attention" and indicate "priority focus here." However, modifications are not limited to these selected paragraphs.

            <Document Content>
            {dumpstr}
            </Document Content>

            <User Instructions>
            {message}
            </User Instructions>

            <Selected Paragraphs>
            {selected_paragraphs}
            </Selected Paragraphs>

            [Editing Requirements]:
            1.  **Core Task**: Modify the [Document Content] according to the [User Instructions].
            2.  **Precise Targeting**:
            - First, analyze any explicit or implicit indications about modification locations in the [User Instructions]. This may include but is not limited to: paragraph numbers, specific text content, relative positions (such as "after paragraph X", "before sentence Y"), or any other clues that help determine the scope of modification.
            - Consider both the user-selected paragraphs and the modification scope analyzed from the user instructions to determine the final modification range, for example:
                - If the user instructions explicitly specify a modification location, such as "add content after the 3rd paragraph," then the 3rd paragraph should be used as the starting point for modification. In this case, the user's selected paragraphs will be ignored. Note that when users refer to paragraph numbers, they typically do not count empty lines.
                - If the user instructions do not explicitly specify a location, use the selected paragraphs as the primary starting point, with discretion to expand based on context.
                - If the user instructions explicitly specify to only modify the selected paragraphs, such as containing phrases like "modify this paragraph," "translate the selected paragraphs," or "only modify the selected content," then only modify the selected paragraphs without changing other paragraphs.
                - If still uncertain, use the selected paragraphs as the primary starting point, with discretion to expand based on context.
            3.  **Faithful Execution**: Ensure your edits accurately reflect the locations and modification intent specified in the [User Instructions].
            4.  **Conflict Resolution**: If these rules conflict with the [User Instructions], prioritize the [User Instructions].

            Please begin editing based on the requirements above.
            
            only output the edited content, with no additional explanations or other words."""
            
            user_prompt = user_prompt_template.format(dumpstr=dumpstr, message=message, selected_paragraphs=selected_paragraphs)
            
            # 如果有选中文本，添加到提示中
            #if selected_text:
            #    user_prompt += f"\n\n选中的文本: {selected_text}"
            
            # 调用LLM生成编辑后的内容
            # 现在整个函数是异步的，可以直接使用 await
            edited_content = await generate_text(
                prompt=user_prompt,
                system_message=system_prompt,
                temperature=0.7,
                streaming=False,
                chat_history=chat_history
            )
            
            # Check if edited_content is empty
            if len(edited_content) == 0:
                logging.error("LLM返回了空内容，无法进行解析")
                # 当内容为空时，返回错误信息而不发送任何动作
                return {
                    "error": "LLM返回了空内容，无法进行解析",
                    "message": message
                }
            else:
                # Parse the edited content and create path-based incremental updates
                path_updates = self._parse_edited_content(edited_content, flattened)
                
                # Return both the full edited content and path-based incremental updates
                # Frontend can choose which approach to use based on its needs
                return {
                    "original": dumpstr,
                    "edited": edited_content,
                    "message": message,
                    "path_updates": path_updates  # Path-based incremental updates
                }
            
        except Exception as e:
            import logging
            logging.error(f"调用LLM编辑文档时出错: {str(e)}", exc_info=True)
            return {
                "original": dumpstr,
                "error": str(e),
                "message": message
            }



def test_pipeline():
    """Test the document pipeline with sample data."""
    # Initialize pipeline with API key
    pipeline = DocumentPipeline(API_KEY)
    
    # Test document path
    test_file = "test_document.md"
    
    # Single prompt for both section finding and editing
    prompt = "Add a new paragraph about Austria's diplomatic relationships."
    
    try:
        # Process the document
        pipeline.process_document(test_file, prompt)
        print("Pipeline test completed successfully")
    except Exception as e:
        print(f"Pipeline test failed: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    test_pipeline()
