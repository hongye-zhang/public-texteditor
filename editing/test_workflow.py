from document_analyzer import DocumentStructureAnalyzer
from edit_planner import EditPlanner
from document_editor import DocumentEditor, EditContext
from test_data import get_document_structure, TEST_PROMPTS

def print_edit_context(context: EditContext):
    print("\nEdit Context:")
    print("-" * 50)
    print(f"Position: {context.position}")
    print("\nCurrent Text:")
    print("-" * 20)
    print(context.current_text)
    print("-" * 20)
    
    if context.before_context:
        print("\nBefore Context:")
        print("-" * 20)
        for ctx in context.before_context:
            print(f"- [{ctx['content_type']}] {ctx['summary']}")
    
    if context.after_context:
        print("\nAfter Context:")
        print("-" * 20)
        for ctx in context.after_context:
            print(f"- [{ctx['content_type']}] {ctx['summary']}")
    
    if context.path:
        print("\nHierarchical Path:")
        print("-" * 20)
        for p in context.path:
            prefix = "  " * (p.get('level', 1) - 1)
            print(f"{prefix}- [{p['type']}] {p.get('text', '')}")

def main():
    # Initialize components
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    analyzer = DocumentStructureAnalyzer(api_key=api_key)
    planner = EditPlanner(api_key=api_key)
    editor = DocumentEditor()
    
    print("1. Getting document structure...")
    structure = get_document_structure(analyzer)
    editor.load_structure(structure)
    
    # Print out positions for debugging
    def print_positions(sections, level=0):
        for section in sections:
            text = section.get('text', '')
            if len(text) > 50:
                text = text[:47] + "..."
            print("  " * level + f"Position {section['position']}: [{section['type']}] {text}")
            if section.get('children'):
                print_positions(section['children'], level + 1)
    
    print("\nDocument Structure with Positions:")
    print("-" * 50)
    print_positions(structure['sections'])
    
    # Test each prompt
    for i, prompt in enumerate(TEST_PROMPTS, 1):
        print(f"\n\nTesting Prompt {i}:")
        print("=" * 80)
        print(f"Prompt: {prompt}")
        print("=" * 80)
        
        # Get edit plan
        plan = planner.plan_edit(structure, prompt)
        print(f"\nEdit Plan:")
        print("-" * 20)
        print(f"Target Position: {plan.target_position}")
        print(f"Edit Type: {plan.edit_type}")
        print(f"Reason: {plan.reason}")
        print(f"Context Positions: {plan.context_positions}")
        
        # Get detailed edit context
        try:
            edit_context = editor.get_edit_context(plan.target_position)
            print_edit_context(edit_context)
        except ValueError as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
