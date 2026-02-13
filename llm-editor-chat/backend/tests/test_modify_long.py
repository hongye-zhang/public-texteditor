import json
import random

def generate_random_hex_id():
    """Generate a random 4-digit hexadecimal ID."""
    return f"{random.randint(0, 0xFFFF):04x}"

def add_ids_to_nodes(node, node_id=None, existing_ids=None):
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
            new_id = generate_random_hex_id()
            while new_id in existing_ids:  # Ensure ID is unique
                new_id = generate_random_hex_id()
            node['id'] = new_id
            existing_ids.add(new_id)
        
        # Recursively process all values in the dictionary
        for key, value in node.items():
            node[key] = add_ids_to_nodes(value, node.get('id'), existing_ids)
            
    elif isinstance(node, list):
        # Process each item in the list
        for i, item in enumerate(node):
            node[i] = add_ids_to_nodes(item, node_id, existing_ids)
    
    return node

def flatten_nodes_to_list(node, result=None):
    """
    Convert the hierarchical JSON structure into a flat list of nodes with IDs and text content.
    The order follows the natural reading order of the document.
    
    Args:
        node: The current node to process
        result: List to store the flattened nodes (used for recursion)
        
    Returns:
        List of dictionaries with 'id' and 'text' keys
    """
    if result is None:
        result = []
    
    if not isinstance(node, (dict, list)):
        return result
        
    # Handle dictionary nodes
    if isinstance(node, dict):
        # Only process nodes with IDs (text nodes and other content nodes)
        if 'id' in node:
            # Handle text nodes
            if node.get('type') == 'text' and 'text' in node:
                result.append({
                    'id': node['id'],
                    'text': node['text']
                })
            # Handle empty paragraphs
            elif node.get('type') == 'paragraph' and not node.get('content'):
                result.append({
                    'id': node['id'],
                    'text': ''  # Empty string for empty paragraphs
                })
        
        # Recursively process all values in the dictionary
        for key, value in node.items():
            flatten_nodes_to_list(value, result)
    
    # Handle lists (like content arrays)
    elif isinstance(node, list):
        for item in node:
            flatten_nodes_to_list(item, result)
    
    return result

tiptapnodestr = '{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"毕达哥拉斯定理是一个关于直角三角形的重要概念。它表明：在直角三角形中，斜边（最长的边）上的平方等于其他两边的平方和。公式是：c² = a² + b²，其中c是斜边，a和b是另外两边。"}]},{"type":"paragraph","content":[{"type":"text","text":"举个例子：假设一个直角三角形的两条直角边分别是3和4，那么斜边c的长度可以用毕达哥拉斯定理计算。根据公式c² = 3² + 4²，我们得到c² = 9 + 16 = 25。因此，c = √25 = 5。所以，这个直角三角形的斜边长度是5。"}]},{"type":"bulletList","attrs":{"tight":true},"content":[{"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","text":"项目1"}]}]},{"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","text":"项目2"}]}]},{"type":"listItem","content":[{"type":"paragraph"}]},{"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","text":"项目3"}]}]}]},{"type":"paragraph"},{"type":"paragraph"},{"type":"paragraph"},{"type":"paragraph"}]}'

# Parse the JSON string
nodejson = json.loads(tiptapnodestr)

# Add unique IDs to all nodes
nodejson_with_ids = add_ids_to_nodes(nodejson)

def print_flattened_nodes(flattened):
    """Print flattened nodes in a readable format."""
    print("\nFlattened nodes (ID: text):")
    print("-" * 80)
    for i, node in enumerate(flattened, 1):
        # Truncate long text for display
        text = node['text']
        if len(text) > 60:
            text = text[:57] + "..."
        print(f"{i:2d}. [ID:{node['id']}] {text}")
    print("-" * 80)
    print(f"Total nodes: {len(flattened)}")

# Print the flattened nodes
flattened = flatten_nodes_to_list(nodejson_with_ids)
print_flattened_nodes(flattened)

# Save the full JSON to a file for reference
with open('flattened_output.json', 'w', encoding='utf-8') as f:
    json.dump(flattened, f, indent=2, ensure_ascii=False)
print("\nFull flattened output has been saved to 'flattened_output.json'")

# Also save the original JSON with IDs
with open('document_with_ids.json', 'w', encoding='utf-8') as f:
    json.dump(nodejson_with_ids, f, indent=2, ensure_ascii=False)
print("Original document with IDs has been saved to 'document_with_ids.json'")
