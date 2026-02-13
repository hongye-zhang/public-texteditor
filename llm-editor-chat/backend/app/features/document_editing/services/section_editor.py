import json
from typing import Dict, Any, List, Tuple, Optional
import difflib
from langchain_openai import ChatOpenAI
import os

class SectionEditor:
    def __init__(self, api_key: str = None):
        """Initialize with OpenAI API key."""
        # Use provided API key or get from environment
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OpenAI API key must be provided or set in OPENAI_API_KEY environment variable")
        
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.3,
            openai_api_key=key
        )
        
    def get_ai_edit(self, prompt: Dict[str, Any]) -> str:
        """Get AI-generated edit in diff format.
        
        Args:
            prompt: Dict containing generated_prompt and sections_extracted
            
        Returns:
            Edit in diff format
        """
        # Extract the original content and prompt
        original_content = prompt["sections_extracted"]["main_section"]
        generated_prompt = prompt["generated_prompt"]
        
        # Create the edit prompt
        edit_prompt = f"{generated_prompt}\n\nOriginal content:\n{original_content}\n\nYour edit:\n"
        
        # Get the edit from the LLM
        response = self.llm.invoke(edit_prompt)
        
        # Extract the diff from the response
        diff = self._extract_diff(response.content)
        return diff

    def _extract_diff(self, response: str) -> str:
        """Extract the diff from the response."""
        # Split the response into lines
        lines = response.split('\n')
        
        # Find the start of the diff
        diff_start = None
        for i, line in enumerate(lines):
            if line.startswith('---'):
                diff_start = i
                break
        
        # If no diff is found, return an empty string
        if diff_start is None:
            return ''
        
        # Extract the diff
        diff = '\n'.join(lines[diff_start:])
        
        return diff

    def generate_diff(self, original: str, modified: str) -> str:
        """Generate a unified diff between original and modified text."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile='original',
            tofile='modified',
            n=3
        )
        
        return ''.join(diff)

    def apply_to_file(self, file_path: str, diff: str, start_line: int, end_line: int) -> None:
        """Apply the edit to the file.
        
        Args:
            file_path: Path to the file to edit
            diff: The diff to apply
            start_line: Start line of the section to edit (0-based)
            end_line: End line of the section to edit (0-based)
        """
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Apply the diff to the section
        section_lines = lines[start_line:end_line + 1]
        section_text = ''.join(section_lines)
        
        # Parse the diff
        patch = self._parse_diff(diff, section_text)
        
        # Apply the patch to create the new section
        new_section_lines = patch.splitlines(keepends=True)
        
        # Replace the old section with the new one
        lines[start_line:end_line + 1] = new_section_lines
        
        # Write back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    def _parse_diff(self, diff: str, original_text: str) -> str:
        """Parse a diff and return the modified text."""
        # Split the diff into lines
        diff_lines = diff.splitlines()
        
        # Skip the header lines
        while diff_lines and (diff_lines[0].startswith('---') or diff_lines[0].startswith('+++')):
            diff_lines.pop(0)
        
        # Apply the changes
        result_lines = original_text.splitlines()
        current_line = 0
        
        for line in diff_lines:
            if not line:
                continue
                
            if line.startswith('@@'):
                # Parse the hunk header
                parts = line.split()
                _, old_range, _, new_range = parts[:4]
                old_start = int(old_range.split(',')[0][1:])
                current_line = old_start - 1
            elif line.startswith('-'):
                # Remove line
                if current_line < len(result_lines):
                    result_lines.pop(current_line)
            elif line.startswith('+'):
                # Add line
                result_lines.insert(current_line, line[1:])
                current_line += 1
            else:
                # Context line
                current_line += 1
        
        return '\n'.join(result_lines) + '\n'

    def generate_edit(self, prompt: Dict[str, Any]) -> str:
        """Generate an edit for the document based on the prompt.
        
        Args:
            prompt: The edit prompt containing section info and user instruction
            
        Returns:
            The edited content as a string
        """
        print("\nGenerating edit based on prompt...")
        
        # Extract the section info
        section_info = prompt.get("sections_extracted", {})
        main_section = section_info.get("main_section", {})
        section_title = main_section.get("title", "Unknown Section")
        
        # Extract the user instruction
        instruction = prompt.get("user_instruction", "")
        
        # Extract the content to edit
        content = prompt.get("content", "")
        
        # Generate a more specific prompt for the LLM
        llm_prompt = f"""You are an expert editor. I need you to edit a section of a document based on a specific instruction.

Section Title: {section_title}
User Instruction: {instruction}

Here is the content to edit:
```
{content}
```

Please provide the COMPLETE edited content that fulfills the user's instruction. 
Make sure to include ALL necessary content, not just the changes.
Your response will directly replace the original content.
Return ONLY the edited content, with no additional explanations or markdown formatting indicators.
"""
        
        print("\nSending prompt to LLM:")
        print(llm_prompt)
        
        # Get the edit from the LLM
        response = self.llm.invoke(llm_prompt)
        
        # Clean up the response - remove any markdown code blocks or explanations
        edited_content = response.content.strip()
        if edited_content.startswith("```") and edited_content.endswith("```"):
            # Remove markdown code blocks
            edited_content = edited_content[edited_content.find("\n")+1:edited_content.rfind("```")].strip()
        
        print("\nLLM Response (cleaned):")
        print(edited_content[:200] + "..." if len(edited_content) > 200 else edited_content)
        
        # Return the cleaned LLM response as the edit
        return edited_content

def test_section_editor():
    """Test the section editor with sample data."""
    # Initialize editor with API key from environment
    editor = SectionEditor()
    
    # Load test prompt
    with open('test_prompt.json', 'r') as f:
        prompt = json.load(f)
    
    # Get AI's edit
    diff = editor.get_ai_edit(prompt)
    print("AI Generated Diff:")
    print(diff)
    
    # Extract line numbers from the prompt text
    import re
    lines_match = re.search(r'Lines: (\d+)-(\d+)', prompt['generated_prompt'])
    if lines_match:
        start_line = int(lines_match.group(1)) - 1  # Convert to 0-based indexing
        end_line = int(lines_match.group(2)) - 1
        
        # Apply the edit to test_document.md
        editor.apply_to_file("test_document.md", diff, start_line, end_line)
        print("\nChanges have been applied to test_document.md")

if __name__ == "__main__":
    test_section_editor()