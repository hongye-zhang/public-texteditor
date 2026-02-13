import json
from typing import Dict, List, Optional

def extract_sections_content(markdown_text: str, section_info: Dict) -> Dict[str, str]:
    """Extract content from the specified sections in the markdown text."""
    sections = {}
    lines = markdown_text.splitlines()
    
    # Extract main section
    if "main_section" in section_info:
        start, end = map(int, section_info["main_section"]["lines"].split("-"))
        sections["main"] = "\n".join(lines[start:end+1])
    
    # Extract supplementary sections
    if "supplementary_sections" in section_info:
        sections["supplementary"] = []
        for supp in section_info["supplementary_sections"]:
            start, end = map(int, supp["lines"].split("-"))
            sections["supplementary"].append({
                "title": supp["title"],
                "summary": supp.get("summary", "")
            })
    
    return sections

def generate_edit_prompt(markdown_text: str, section_info: Dict, user_prompt: str) -> str:
    """
    Generate a prompt for an LLM to create a diff-format edit based on section information.
    
    Args:
        markdown_text: The full markdown text content
        section_info: Dict containing main and supplementary section information
        user_prompt: The user's editing request/prompt
        
    Returns:
        str: A formatted prompt for the LLM
    """
    sections = extract_sections_content(markdown_text, section_info)
    
    prompt = f"""You are an expert editor. I need you to edit a section of text based on specific requirements.

TASK:
Edit the following section based on this request: {user_prompt}

MAIN SECTION TO EDIT:
Title: {section_info['main_section']['title']}
Lines: {section_info['main_section']['lines']}
Current content:
{sections['main']}

CONTEXT:"""

    if sections.get("supplementary"):
        prompt += "\nThe following context is relevant for the edit:"
        for idx, supp in enumerate(sections["supplementary"]):
            prompt += f"""

{supp['title']} (lines {section_info['supplementary_sections'][idx]['lines']}):
{supp['summary']}"""

    prompt += """

REQUIREMENTS:
1. Generate a unified diff format edit that shows how to modify the main section
2. Use --- and +++ to indicate file changes
3. Use - for removed lines and + for added lines
4. Include @@ markers to show the line range being modified
5. Preserve the section's meaning while improving clarity and detail
6. Use the supplementary context to inform your edits
7. Keep the edit focused on the main section only

OUTPUT FORMAT:
Provide ONLY the unified diff format edit, like this example:
--- original
+++ edited
@@ -1,3 +1,4 @@
 unchanged line
-removed line
+added line
+another added line
 unchanged line

Your edit:
"""
    
    return prompt

def test_prompt_generator():
    """Test the prompt generator with sample data."""
    # Sample markdown text
    with open("test_document.md", "r") as f:
        markdown_text = f.read()
    
    # Sample section info
    section_info = {
  "status": "success",
  "main_section": {
    "title": "Austria plans for war",
    "lines": "21-30"
  },
  "supplementary_sections": [
    {
      "title": "Peninsular War",
      "lines": "11-20",
      "summary": "Provides information on Austria's involvement in the Peninsular War, which may have influenced their decision to go to war."      
    },
    {
      "title": "Background",
      "lines": "1-30",
      "summary": "Offers a broader context that may explain the factors leading to Austria's decision to go to war."
    }
  ]
}
    
    # Sample user prompt
    user_prompt = "Expand on Austria's motivations for going to war and their diplomatic efforts"
    
    # Generate prompt
    prompt = generate_edit_prompt(markdown_text, section_info, user_prompt)
    
    # Output as JSON for clean formatting
    output = {
        "generated_prompt": prompt,
        "sections_extracted": extract_sections_content(markdown_text, section_info)
    }
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    test_prompt_generator()
