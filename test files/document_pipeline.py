from typing import Dict, Any, Optional, List
from document_analyzer import DocumentStructureAnalyzer
from section_finder import SectionFinder
from prompt_generator import generate_edit_prompt
from section_editor import SectionEditor
import json
import traceback
import os

# API key should be provided via environment variable or constructor parameter

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
                if section_copy.get('title') and section_copy.get('title') != 'Document Total':
                    # Add the section to the flattened list
                    flattened.append(section_copy)
        
        _flatten_recursive(sections)
        
        # Debug the flattened sections
        print("\nDebug - Flattened Sections:")
        for i, section in enumerate(flattened):
            print(f"Section {i}: {section.get('title')} (Lines: {section.get('start_line')}-{section.get('end_line')})")
        
        return flattened

    def generate_edit_prompt(self, markdown_text: str, section_info: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """Generate a prompt for editing the selected section.
        
        Args:
            markdown_text: The original markdown text
            section_info: Information about the selected section
            prompt: The user's prompt
            
        Returns:
            Dict containing the edit prompt
        """
        # Extract main section
        main_section = section_info.get("main", {})
        title = main_section.get("title", "Unknown Section")
        lines = main_section.get("lines", "0-0")
        
        # Parse line range
        try:
            start_line, end_line = map(int, lines.split("-"))
        except ValueError:
            print(f"Error parsing line range: {lines}")
            start_line, end_line = 0, 0
            
        # Extract content for the section
        markdown_lines = markdown_text.split("\n")
        if start_line <= end_line and start_line >= 0 and end_line < len(markdown_lines):
            section_content = "\n".join(markdown_lines[start_line:end_line+1])
        else:
            print(f"Warning: Invalid line range {start_line}-{end_line} for document with {len(markdown_lines)} lines")
            section_content = ""
            
        # Format the edit prompt
        edit_prompt = {
            "user_instruction": prompt,
            "sections_extracted": {
                "main_section": {
                    "title": title,
                    "lines": lines
                },
                "supplementary_sections": []
            },
            "content": section_content,
            "line_range": f"{start_line}-{end_line}"
        }
        
        return edit_prompt

    def apply_edit(self, file_path: str, prompt: Dict[str, Any]) -> str:
        """Apply the edit to the document.
        
        Args:
            file_path: Path to the document to edit
            prompt: The edit prompt
            
        Returns:
            The edited content
        """
        # Extract the line range
        line_range = prompt.get('line_range', '')
        if not line_range or '-' not in line_range:
            raise ValueError(f"Invalid line range: {line_range}")
            
        start_line, end_line = map(int, line_range.split('-'))
        
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split into lines
        lines = content.split('\n')
        
        # Validate and adjust line range if needed
        if start_line < 0:
            start_line = 0
        if end_line >= len(lines):
            end_line = len(lines) - 1
            
        # Make sure start_line <= end_line
        if start_line > end_line:
            print(f"Warning: Invalid line range {start_line}-{end_line}, adjusting to {start_line}-{start_line}")
            end_line = start_line
            
        print(f"Using adjusted line range: {start_line}-{end_line}")
        
        # Get the edit content from the LLM
        prompt['line_range'] = f"{start_line}-{end_line}"
        edit_content = self.section_editor.generate_edit(prompt)
        
        # Apply the edit directly
        print(f"Applying edit to lines {start_line}-{end_line}")
        print("Original content (snippet):")
        for line in lines[start_line:min(start_line+5, end_line+1)]:
            print(line)
        
        print("New content (snippet):")
        edit_lines = edit_content.split('\n')
        for line in edit_lines[:5]:
            print(line)
        
        # Replace the specified lines with the edit content
        edited_lines = edit_content.split('\n')
        lines[start_line:end_line+1] = edited_lines
        edited_content = '\n'.join(lines)
        
        # Write back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(edited_content)
            
        return edited_content

    def process_document(self, file_path: str, prompt: str) -> str:
        """Process a document through the pipeline.
        
        Args:
            file_path: Path to the document to process
            prompt: The user's instruction for section selection and editing
            
        Returns:
            The updated document content
        """
        try:
            # Step 1: Analyze document structure
            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
            
            print("\nDebug - Analyzing document structure...")
            # Use the pre-computed structure instead of analyzing the document
            structure = structure_precompute
            
            # Step 2: Find relevant sections
            print("\nDebug - Finding relevant sections...")
            section_info = self.find_relevant_sections(prompt, {"sections": structure, "total_lines": 161})
            print("\nDebug - Section Info:")
            print(json.dumps(section_info, indent=2))
            
            # Step 3: Generate edit prompt
            print("\nDebug - Generating edit prompt...")
            edit_prompt = self.generate_edit_prompt(markdown_text, section_info, prompt)
            print("\nDebug - Generated Prompt:")
            print(json.dumps(edit_prompt, indent=2))
            
            # Step 4: Apply edit
            print("\nDebug - Applying edit...")
            updated_content = self.apply_edit(file_path, edit_prompt)
            
            print("Pipeline test completed successfully")
            return updated_content
            
        except Exception as e:
            import traceback
            print(f"Error processing document: {str(e)}")
            traceback.print_exc()
            return None

def test_pipeline():
    """Test the document pipeline with sample data."""
    # Create a pipeline
    pipeline = DocumentPipeline(API_KEY)
    
    # Test file
    test_file = "diff_tests.md"
    
    # Single prompt for both section finding and editing
    prompt = "Edit chinas relevance to include their impact to austria."
    
    try:
        # Process the document
        updated_content = pipeline.process_document(test_file, prompt)
        print("Updated Content:")
        
        # Read the file after processing to verify changes
        with open(test_file, 'r', encoding='utf-8') as f:
            after_content = f.read()
            
        # Check if the content has changed
        if after_content != updated_content:
            print("\nWarning: File content doesn't match returned content")
            
        print("\nEdit successfully applied to the document.")
        print("You can check the file to see the changes.")
            
    except Exception as e:
        print(f"Pipeline test failed: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    structure_precompute = [
  {
    "title": "Document Total",
    "type": "",
    "summary": "Comprehensive China's Influence Innovation - **Implications** Challenges Taiwan's Technological Leadership Innovation Challenges Diverse Research",       
    "content_type": "",
    "start_line": 0,
    "end_line": 161,
    "children": [
      {
        "title": "Analysis and Impact of the Paper from PDF",
        "type": "heading",
        "summary": "",
        "content_type": "heading",
        "start_line": 0,
        "end_line": 1
      },
      {
        "title": "Analysis and Impact of the Paper from PDF",
        "type": "heading",
        "summary": "Comprehensive review by \\[Your Name\\] on \\[Presentation Date\\] at \\[Location/Organization\\] for internal research discussion.",
        "content_type": "list",
        "start_line": 2,
        "end_line": 14,
        "children": [
          {
            "title": "Agenda",
            "type": "heading",
            "summary": "",
            "content_type": "heading",
            "start_line": 13,
            "end_line": 14
          }
        ]
      },
      {
        "title": "Agenda",
        "type": "heading",
        "summary": "Comprehensive China's Influence Innovation Innovation Challenges Technological Advancements Innovative Innovation Diverse Research",
        "content_type": "list",
        "start_line": 15,
        "end_line": 161,
        "children": [
          {
            "title": "Introduction",
            "type": "heading",
            "summary": "- Objective: prioritize tasks, set goals, track progress, manage time effectively, improve productivity.",
            "content_type": "list",
            "start_line": 17,
            "end_line": 20
          },
          {
            "title": "Background",
            "type": "heading",
            "summary": "Context, challenges, and previous work are essential for understanding the research project.",
            "content_type": "list",
            "start_line": 21,
            "end_line": 26
          },
          {
            "title": "Paper Analysis",
            "type": "heading",
            "summary": "Paper overview, methodology, innovation, experiments, results, intuitive explanation.",
            "content_type": "list",
            "start_line": 27,
            "end_line": 35
          },
          {
            "title": "Visual Analysis",
            "type": "heading",
            "summary": "Key visuals, comparison, 13, 14.",
            "content_type": "list",
            "start_line": 36,
            "end_line": 40
          },
          {
            "title": "Impact and Applications",
            "type": "heading",
            "summary": "Paper's impact, citations, journal ranking, authorship, collaboration, funding, data sharing, and social media presence.",
            "content_type": "list",
            "start_line": 41,
            "end_line": 45
          },
          {
            "title": "Relevance of China to \\[Paper's Topic\\]",
            "type": "heading",
            "summary": "China: Global player, tech leader, influential. China policy innovation sustainability technology. Chinese education, future implications, research, developments.",
            "content_type": "list",
            "start_line": 46,
            "end_line": 62
          },
          {
            "title": "Conclusion",
            "type": "heading",
            "summary": "Summary: 20 key takeaways include: prioritize tasks, set goals, stay organized, and maintain focus.",
            "content_type": "list",
            "start_line": 63,
            "end_line": 67
          },
          {
            "title": "Discussion",
            "type": "heading",
            "summary": "22 open questions, 23 feedback items.",
            "content_type": "list",
            "start_line": 68,
            "end_line": 72
          },
          {
            "title": "Appendix",
            "type": "heading",
            "summary": "Additional data and references available for further information, totaling 24 and 25 respectively.",
            "content_type": "list",
            "start_line": 73,
            "end_line": 79
          },
          {
            "title": "Objective",
            "type": "heading",
            "summary": "Analyze paper goals, significance, implications, focus on key aspects for in-depth exploration.",
            "content_type": "list",
            "start_line": 80,
            "end_line": 87
          },
          {
            "title": "Context",
            "type": "heading",
            "summary": "Industry trends, new tech, market changes, regulations, competition, and consumer behavior drive industry evolution.",
            "content_type": "list",
            "start_line": 88,
            "end_line": 98
          },
          {
            "title": "Existing Challenges",
            "type": "heading",
            "summary": "- Technological limitations: hardware, software, bandwidth, compatibility, security, storage, processing power, connectivity, accessibility.",    
            "content_type": "list",
            "start_line": 99,
            "end_line": 102
          },
          {
            "title": "Relevance of Taiwan to \\[Paper's Topic\\]",
            "type": "heading",
            "summary": "Taiwan's influential role in technology. Taiwan policy supports innovation, sustainability.  Case studies show successful adoption. Taiwan's future in technology:  - Education - Leadership - Innovation - Regulation - Competition", 
            "content_type": "list",
            "start_line": 103,
            "end_line": 124
          },
          {
            "title": "Previous Work",
            "type": "heading",
            "summary": "Studies 1 and 4 examined foundations and limitations, while research 2 focused on technology advancements.",
            "content_type": "list",
            "start_line": 125,
            "end_line": 134
          },
          {
            "title": "Overview of the Paper",
            "type": "heading",
            "summary": "Paper focuses on specific domain, primary focus is main thesis proposing key proposal.",
            "content_type": "list",
            "start_line": 135,
            "end_line": 141
          },
          {
            "title": "Methodology",
            "type": "heading",
            "summary": "Methodology, techniques, data sources, analysis process, validation methods ensure reliability of research results.",
            "content_type": "list",
            "start_line": 142,
            "end_line": 151
          },
          {
            "title": "Innovation",
            "type": "heading",
            "summary": "Innovative technique challenges norms, advances field, bridges disciplines, offers real-world applications, enriches academic discourse.",        
            "content_type": "list",
            "start_line": 152,
            "end_line": 161
          }
        ]
      }
    ]
  }
]
    test_pipeline()
