from fastapi import APIRouter, HTTPException
from typing import List

from app.features.document_tree.models import TreeItem, DocumentTreeRequest, DocumentTreeResponse
from app.features.document_tree.services.document_tree_service import save_document_tree, get_document_tree

router = APIRouter(prefix="/document", tags=["document-tree"])

@router.post("/tree", response_model=DocumentTreeResponse)
async def save_document_tree_endpoint(request: DocumentTreeRequest):
    """Save document tree structure sent from the frontend"""
    try:
        # Use the document tree service to save the document tree
        storage_key = await save_document_tree(request.document_tree, request.file_id)
        
        return DocumentTreeResponse(
            success=True, 
            message="Document tree saved successfully", 
            tree_id=storage_key
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving document tree: {str(e)}")

@router.get("/tree/{tree_id}", response_model=List[TreeItem])
async def get_document_tree_endpoint(tree_id: str):
    """Get a document tree by its ID"""
    try:
        # Use the document tree service to get the document tree
        return await get_document_tree(tree_id)
    except FileNotFoundError:
        # If the document tree is not found
        raise HTTPException(status_code=404, detail=f"Document tree with ID {tree_id} not found")
    except Exception as e:
        # For any other errors
        raise HTTPException(status_code=500, detail=f"Error retrieving document tree: {str(e)}")
