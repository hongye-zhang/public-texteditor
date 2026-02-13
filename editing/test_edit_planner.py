from document_analyzer import DocumentStructureAnalyzer
from edit_planner import EditPlanner
import os

# Initialize with API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

analyzer = DocumentStructureAnalyzer(api_key=api_key)
planner = EditPlanner(api_key=api_key)

# Test document
markdown_text = """# William Dempster Hoard

William Dempster Hoard (October 10, 1836 – November 22, 1918) was an American politician and agriculture advocate.

## Early Life and Education

William D. Hoard was born on October 10, 1836, in Munnsville, New York. He was educated in a one-room log schoolhouse.

## Career

### Publishing and Advocacy

Hoard founded a weekly newspaper, the Jefferson County Union, in Lake Mills in 1870.
"""

# First, analyze the document
structure = analyzer.analyze_docx(markdown_text)

# Test different edit requests
test_prompts = [
    "Add more details about his achievements in the first paragraph",
    "Add a new section about his family life under Early Life",
    "Update the Career section to include his role as governor"
]

for prompt in test_prompts:
    print(f"\nTesting prompt: {prompt}")
    print("-" * 50)
    
    # Get edit plan
    plan = planner.plan_edit(structure, prompt)
    print(f"Edit Plan:")
    print(f"- Target Position: {plan.target_position}")
    print(f"- Edit Type: {plan.edit_type}")
    print(f"- Reason: {plan.reason}")
    print(f"- Context Positions: {plan.context_positions}")
    
    # Get sections with context
    context = planner.get_edit_context(structure, plan)
    print("\nTarget Section:")
    print(f"Type: {context['target_section']['type']}")
    print(f"Content: {context['target_section'].get('text', '')[:100]}...")
    
    print("\nContext Sections:")
    for section in context['context_sections']:
        print(f"- {section.get('text', '')[:100]}...")
