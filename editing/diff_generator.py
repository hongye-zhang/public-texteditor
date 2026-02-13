import json
import difflib
from typing import Dict, List, Optional

def generate_section_diff(file_path: str, section_info: Dict, new_content: str) -> Dict:
    """
    Generate a diff for editing a section in a text file.
    
    Args:
        file_path: Path to the text file
        section_info: Dict containing section information (title and line range)
        new_content: New content to replace the section with
        
    Returns:
        Dict containing the diff and affected lines
    """
    # Read the original file
    with open(file_path, 'r') as f:
        original_lines = f.readlines()
    
    # Get the section's line range
    start_line, end_line = map(int, section_info['lines'].split('-'))
    
    # Create list of new lines
    new_lines = new_content.splitlines(keepends=True)
    
    # Create a copy of original lines and replace the section
    modified_lines = original_lines.copy()
    modified_lines[start_line:end_line + 1] = new_lines
    
    # Generate unified diff
    diff = list(difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"{file_path} (current)",
        tofile=f"{file_path} (proposed)",
        fromfiledate=f"section: {section_info['title']}",
        tofiledate="edited content",
        n=3  # Context lines
    ))
    
    # Create windsurf-style output
    windsurf = [
        f"@@ Editing section: {section_info['title']} (lines {start_line}-{end_line}) @@\n",
        "Current content:\n"
    ]
    windsurf.extend(f"- {line}" for line in original_lines[start_line:end_line + 1])
    windsurf.append("\nNew content:\n")
    windsurf.extend(f"+ {line}" for line in new_lines)
    
    return {
        "diff": "".join(diff),
        "windsurf": "".join(windsurf),
        "affected_lines": {
            "start": start_line,
            "end": end_line,
            "new_line_count": len(new_lines)
        }
    }

def test_diff_generator():
    """Test the diff generator with sample data."""
    # Sample section finder results
    results = {
        "status": "success",
        "main_section": {
            "title": "Austria plans for war",
            "lines": "21-30"
        },
        "supplementary_sections": [
            {
                "title": "Peninsular War",
                "lines": "11-20",
                "summary": "Provides information on Austria's involvement in the Peninsular War..."
            },
            {
                "title": "Background",
                "lines": "1-30",
                "summary": "Offers a broader context..."
            }
        ]
    }
    
    # Sample new content
    new_content = """Austria, seeking to break free from French influence, began planning for war.
They first approached Prussia for support but faced setbacks when France intervened.
After Stein's exile and French troop withdrawals, they sought British aid alongside Prussia."""
    
    # Generate diff
    diff_output = generate_section_diff(
        "test_document.md",
        results["main_section"],
        new_content
    )
    
    # Output as JSON
    print(json.dumps(diff_output, indent=2))

if __name__ == "__main__":
    test_diff_generator()
