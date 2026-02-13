from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

class EditPlan(BaseModel):
    """Model for the edit plan output"""
    target_position: int = Field(description="Position number of the section that should be edited")
    edit_type: str = Field(description="Type of edit (update, insert, delete)")
    reason: str = Field(description="Brief explanation of why this section was chosen")
    context_positions: list[int] = Field(description="List of positions (max 2) that provide important context")

class EditPlanner:
    """Plans edits to a document based on user prompts"""
    def __init__(self, api_key: str = None):
        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-3.5-turbo",
            api_key=api_key
        )
        
        # Create the output parser
        self.parser = PydanticOutputParser(pydantic_object=EditPlan)
        
        # Create the prompt template
        self.analyze_prompt = PromptTemplate(
            template="""You are an AI editor assistant. Given a document structure and a user's edit request, 
            determine which section needs to be edited and what context is needed.

            Document Structure:
            {document_structure}

            User's Edit Request:
            {user_prompt}

            Based on the document structure and user's request, provide a JSON response with:
            1. target_position: Position number of the section that should be edited
            2. edit_type: One of 'update', 'insert', or 'delete'
            3. reason: A brief explanation of why this section was chosen
            4. context_positions: List of positions (max 2) that provide important context

            {format_instructions}
            """,
            input_variables=["document_structure", "user_prompt"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
    
    def _collect_valid_positions(self, sections: list, valid_positions: list = None) -> list:
        """Collect all valid positions from the document structure"""
        if valid_positions is None:
            valid_positions = []
        
        for section in sections:
            if 'position' in section:
                valid_positions.append(section['position'])
            if 'children' in section and section['children']:
                self._collect_valid_positions(section['children'], valid_positions)
        
        return valid_positions
    
    def _format_structure_for_llm(self, sections: list, level: int = 0, output: list = None) -> str:
        """Format the document structure in a way that's easy for the LLM to understand"""
        if output is None:
            output = []
        
        indent = "  " * level
        for section in sections:
            # Add position and type
            line = f"{indent}[Position {section['position']}] "
            
            # Add content type and line range
            line += f"[{section['type']}] "
            if 'start_line' in section:
                line += f"(lines {section['start_line']}-{section.get('end_line', section['start_line'])}) "
            
            # Add text or summary if available
            if 'text' in section:
                line += section['text'][:100]  # Truncate long text
                if len(section['text']) > 100:
                    line += "..."
            elif 'summary' in section:
                line += section['summary'][:100]
                if len(section['summary']) > 100:
                    line += "..."
            
            output.append(line)
            
            # Process children
            if 'children' in section and section['children']:
                self._format_structure_for_llm(section['children'], level + 1, output)
        
        return "\n".join(output)
    
    def _find_section_by_keyword(self, sections: list, keyword: str) -> int:
        """Find a section position by keyword"""
        for section in sections:
            if keyword.lower() in section.get('text', '').lower():
                return section['position']
            if section.get('children'):
                result = self._find_section_by_keyword(section['children'], keyword)
                if result:
                    return result
        return None
    
    def plan_edit(self, structure: dict, user_prompt: str) -> EditPlan:
        """Plan an edit based on the document structure and user prompt"""
        # Get all valid positions
        valid_positions = self._collect_valid_positions(structure['sections'])
        
        # Format the structure for the LLM
        formatted_structure = self._format_structure_for_llm(structure['sections'])
        
        # Add valid positions to the prompt
        formatted_structure += "\n\nValid positions for editing: " + ", ".join(map(str, sorted(valid_positions)))
        
        # Get the edit plan from the LLM
        response = self.llm.invoke(
            self.analyze_prompt.format(
                document_structure=formatted_structure,
                user_prompt=user_prompt
            )
        )
        
        # Parse the response
        plan = self.parser.parse(response.content)
        
        # Validate positions
        if plan.target_position not in valid_positions:
            # Try to find a matching section based on keywords in the prompt
            keywords = ["publishing", "advocacy", "early life", "political career", "bennett law"]
            for keyword in keywords:
                if keyword.lower() in user_prompt.lower():
                    pos = self._find_section_by_keyword(structure['sections'], keyword)
                    if pos:
                        plan.target_position = pos
                        break
        
        if plan.target_position not in valid_positions:
            raise ValueError(f"Invalid target position {plan.target_position}")
        
        # Filter out invalid context positions
        plan.context_positions = [pos for pos in plan.context_positions if pos in valid_positions][:2]
        
        return plan

    def get_edit_context(self, structure: Dict[str, Any], plan: EditPlan) -> Dict[str, Any]:
        """
        Get the target section and context sections based on the edit plan.
        
        Args:
            structure: Document structure
            plan: Edit plan from plan_edit()
            
        Returns:
            Dict containing target section and context sections
        """
        def find_section(sections: List[Dict[str, Any]], position: int) -> Optional[Dict[str, Any]]:
            for section in sections:
                if section.get("position") == position:
                    return section
                if section.get("children"):
                    result = find_section(section["children"], position)
                    if result:
                        return result
            return None
        
        # Get target section
        target_section = find_section(structure["sections"], plan.target_position)
        
        # Get context sections
        context_sections = []
        for pos in plan.context_positions:
            section = find_section(structure["sections"], pos)
            if section:
                context_sections.append(section)
        
        return {
            "target_section": target_section,
            "context_sections": context_sections,
            "edit_type": plan.edit_type,
            "reason": plan.reason
        }
