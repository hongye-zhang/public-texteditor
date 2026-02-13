import json
from typing import Dict, Optional
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
import difflib
import os

class SectionEditor:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the section editor with OpenAI API key."""
        self.llm = ChatOpenAI(
            model_name="gpt-4o",
            temperature=0.7,
            openai_api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
        
    def get_ai_edit(self, prompt: Dict) -> str:
        """
        Get an edited version of the section from the AI.
        
        Args:
            prompt: Dictionary containing the generated prompt and extracted sections
            
        Returns:
            str: The AI's response in diff format
        """
        # Extract the main section content
        original_content = prompt["sections_extracted"]["main"]
        
        # Get AI's response
        messages = [
            HumanMessage(content=prompt["generated_prompt"])
        ]
        
        response = self.llm.invoke(messages)
        
        # The response should be in diff format, but let's validate and clean it
        diff_lines = response.content.strip().split('\n')
        
        # Ensure it starts with --- and +++
        if not (diff_lines[0].startswith('---') and diff_lines[1].startswith('+++')):
            # If not in diff format, generate diff ourselves
            new_content = response.content.strip()
            diff = self.generate_diff(original_content, new_content)
            return diff
            
        return response.content.strip()
        
    def generate_diff(self, original: str, modified: str) -> str:
        """Generate a unified diff between original and modified text."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile='original',
            tofile='edited',
            n=3  # Context lines
        ))
        
        return ''.join(diff)
        
    def apply_edit(self, original_text: str, diff_text: str) -> str:
        """
        Apply a diff to the original text.
        
        Args:
            original_text: The original text content
            diff_text: The diff to apply
            
        Returns:
            str: The modified text
        """
        # Split into lines
        lines = original_text.splitlines(keepends=True)
        
        # Parse the diff
        diff_lines = diff_text.split('\n')
        
        # Skip the header lines (---, +++, @@)
        content_lines = []
        i = 0
        while i < len(diff_lines):
            line = diff_lines[i]
            if line.startswith('@@'):
                i += 1
                break
            i += 1
            
        # Apply the changes
        result = []
        original_index = 0
        
        while i < len(diff_lines):
            line = diff_lines[i]
            if not line:
                i += 1
                continue
                
            if line.startswith(' '):
                # Unchanged line
                result.append(lines[original_index])
                original_index += 1
            elif line.startswith('-'):
                # Removed line
                original_index += 1
            elif line.startswith('+'):
                # Added line
                result.append(line[1:] + '\n')
            
            i += 1
            
        return ''.join(result)

    def apply_to_file(self, file_path: str, diff_text: str, start_line: int, end_line: int) -> None:
        """
        Apply a diff to a specific section of a file.
        
        Args:
            file_path: Path to the file to modify
            diff_text: The diff text to apply
            start_line: Starting line of the section (0-based)
            end_line: Ending line of the section (0-based)
        """
        # Read the entire file
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Extract the modified content from the diff
        # Skip the metadata lines (---, +++, @@)
        diff_lines = diff_text.strip().split('\n')
        modified_lines = []
        content_started = False
        
        for line in diff_lines:
            if line.startswith('@@'):
                content_started = True
                continue
            if not content_started:
                continue
            if line.startswith('+'):
                modified_lines.append(line[1:])
        
        # Replace the section in the file
        lines[start_line:end_line + 1] = modified_lines
        
        # Write back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

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