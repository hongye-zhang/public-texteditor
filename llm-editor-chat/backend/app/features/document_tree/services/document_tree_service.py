"""
Document Tree Service

This module provides services for managing document tree structures.
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

from app.features.document_tree.models import TreeItem

# In-memory storage for document trees (in a real app, this would be a database)
document_trees: Dict[str, List[TreeItem]] = {}

async def save_document_tree(document_tree: List[TreeItem], file_id: Optional[str] = None) -> str:
    """
    Save a document tree structure
    
    Args:
        document_tree: The document tree structure to save
        file_id: Optional file ID to associate with the document tree
        
    Returns:
        str: The storage key (tree_id) for the saved document tree
    """
    # Generate a key for storage - either use the file_id or a timestamp
    storage_key = file_id if file_id else f"tree_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Store the document tree
    document_trees[storage_key] = document_tree
    
    # Optionally save to a file for persistence
    try:
        os.makedirs("temp/document_trees", exist_ok=True)
        with open(f"temp/document_trees/{storage_key}.json", "w") as f:
            # Convert to dict for JSON serialization
            tree_dict = [item.dict() for item in document_tree]
            json.dump(tree_dict, f, indent=2)
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Error saving document tree to file: {str(e)}")
    
    return storage_key

async def get_document_tree(tree_id: str) -> List[TreeItem]:
    """
    Get a document tree by its ID
    
    Args:
        tree_id: The ID of the document tree to retrieve
        
    Returns:
        List[TreeItem]: The document tree structure
        
    Raises:
        FileNotFoundError: If the document tree is not found
    """
    # First try to get from memory
    if tree_id in document_trees:
        return document_trees[tree_id]
    
    # If not in memory, try to load from file
    file_path = f"temp/document_trees/{tree_id}.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            tree_data = json.load(f)
            # Convert back to TreeItem objects
            return [TreeItem(**item) for item in tree_data]
    
    # If not found anywhere
    raise FileNotFoundError(f"Document tree with ID {tree_id} not found")
