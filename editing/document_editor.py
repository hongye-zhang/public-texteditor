from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class EditOperation(Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"

@dataclass
class EditContext:
    """Context needed for editing a specific position in the document"""
    position: int
    current_text: str
    before_context: List[Dict[str, Any]]  # Previous paragraphs/sections
    after_context: List[Dict[str, Any]]   # Following paragraphs/sections
    path: List[Dict[str, Any]]            # Hierarchical path to current position

class DocumentEditor:
    def __init__(self):
        self.structure = None
        
    def load_structure(self, structure: Dict[str, Any]):
        """Load document structure from analyzer"""
        self.structure = structure
        
    def get_edit_context(self, position: int, window_size: int = 2) -> EditContext:
        """
        Get the minimal context needed for editing at a specific position.
        
        Args:
            position: The position to edit
            window_size: Number of surrounding paragraphs to include
            
        Returns:
            EditContext containing essential information for editing
        """
        if not self.structure:
            raise ValueError("No document structure loaded")
            
        def find_in_sections(sections: List[Dict[str, Any]], pos: int) -> Optional[EditContext]:
            context = {
                "before": [],
                "current": None,
                "after": [],
                "path": []
            }
            
            # First pass: collect all sections in order
            all_sections = []
            def collect_sections(sections_list):
                for section in sections_list:
                    all_sections.append(section)
                    if section.get("children"):
                        collect_sections(section["children"])
            
            collect_sections(sections)
            
            # Find the target section and build context
            target_idx = None
            for idx, section in enumerate(all_sections):
                if section.get("position") == pos:
                    target_idx = idx
                    context["current"] = section
                    break
            
            if target_idx is not None:
                # Get before context
                start_idx = max(0, target_idx - window_size)
                for idx in range(start_idx, target_idx):
                    section = all_sections[idx]
                    context["before"].append({
                        "summary": section.get("summary", ""),
                        "content_type": section.get("content_type", ""),
                        "position": section.get("position")
                    })
                
                # Get after context
                end_idx = min(len(all_sections), target_idx + window_size + 1)
                for idx in range(target_idx + 1, end_idx):
                    section = all_sections[idx]
                    context["after"].append({
                        "summary": section.get("summary", ""),
                        "content_type": section.get("content_type", ""),
                        "position": section.get("position")
                    })
                
                # Build path by traversing up through sections
                current_section = context["current"]
                while current_section:
                    parent_found = False
                    for section in all_sections:
                        if section.get("children") and current_section in section["children"]:
                            context["path"].insert(0, {
                                "type": section["type"],
                                "text": section.get("text", ""),
                                "level": section.get("level"),
                                "content_type": section.get("content_type", "")
                            })
                            current_section = section
                            parent_found = True
                            break
                    if not parent_found:
                        break
                
                return EditContext(
                    position=pos,
                    current_text=context["current"].get("text", ""),
                    before_context=context["before"],
                    after_context=context["after"],
                    path=context["path"]
                )
            
            return None
            
        edit_context = find_in_sections(self.structure["sections"], position)
        if not edit_context:
            raise ValueError(f"Position {position} not found in document")
            
        return edit_context

    def apply_edit(self, position: int, operation: EditOperation, new_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Apply an edit operation at the specified position.
        
        Args:
            position: Position to edit
            operation: Type of edit operation
            new_text: New text for INSERT or UPDATE operations
            
        Returns:
            Updated document structure
        """
        # TODO: Implement edit operations
        pass
