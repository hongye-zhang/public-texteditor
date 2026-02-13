from typing import List, Dict, Any

async def execute_actions(
    original_content: str,
    actions: List[Dict[str, Any]]
) -> str:
    """
    Execute a list of actions on the original content and return the updated content.
    Supported actions:
    - insert: append or insert content
    - replace_all: replace full content with new content
    - delete: remove content or lines
    """
    content = original_content
    for action in actions:
        action_type = action.get('type')
        payload = action.get('payload', {})
        if action_type == 'insert':
            # Append content at the end without including original content
            content = payload.get('content', '')
        elif action_type == 'replace_all':
            # Replace entire content
            content = payload.get('content', '')
        # TODO: add more action types
    return content
