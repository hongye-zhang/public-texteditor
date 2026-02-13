"""
Document Tree Models

This module contains the data models for the document tree feature.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class TreeItem(BaseModel):
    """Document tree item model"""
    id: str
    level: int
    text: str
    position: int
    children: List["TreeItem"] = []

class DocumentTreeRequest(BaseModel):
    """Document tree request model"""
    document_tree: List[TreeItem]
    file_id: Optional[str] = None

class DocumentTreeResponse(BaseModel):
    """Document tree response model"""
    success: bool
    message: str
    tree_id: str
