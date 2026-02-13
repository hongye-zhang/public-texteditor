from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import json

class SectionFinder:
    def __init__(self, api_key: str):
        """Initialize with OpenAI API key."""
        self.llm = ChatOpenAI(
            api_key=api_key,
            model_name="gpt-3.5-turbo",
            temperature=0.3
        )
        
        # Create the prompt template for section analysis
        self.section_prompt = PromptTemplate(
            template="""Given a user's query and document sections, determine which section is most relevant for addressing their request.

Query: {query}

Document Sections:
{sections}

Instructions:
1. Identify the main section that is most relevant to the query
2. Identify any supplementary sections that provide additional context
3. Return a JSON object in EXACTLY this format, with no additional text:
{{
    "main": {{
        "title": "section_title",
        "lines": "start_line-end_line"
    }},
    "supplement": [
        {{
            "title": "section_title",
            "lines": "start_line-end_line",
            "summary": "brief_summary"
        }}
    ]
}}

Remember to:
- Focus on sections most relevant to the query
- Include exact line numbers for precise navigation
- Keep summaries concise but informative
- Consider both direct matches and related context""",
            input_variables=["query", "sections"]
        )

    def format_sections(self, doc_structure: Dict[str, Any]) -> str:
        """Format document sections for the prompt."""
        sections_text = []
        
        def process_section(section: Dict[str, Any], depth: int = 0):
            section_info = f"{'  ' * depth}Title: {section['title']}"
            section_info += f"\nLines: {section['start_line']}-{section['end_line']}"
            if 'content' in section:
                content = section['content']
                if len(content) > 500:
                    content = content[:500] + "..."
                section_info += f"\nContent: {content[:200]}..."
            sections_text.append(section_info)
            
            for child in section.get('children', []):
                process_section(child, depth + 1)
        
        for section in doc_structure['sections']:
            process_section(section)
            
        return "\n\n".join(sections_text)

    async def find_relevant_sections(self, text: str, query: str, doc_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Find the most relevant sections based on the user's query."""
        sections_text = self.format_sections(doc_structure)
        
        # Get LLM response
        response = await self.section_prompt.ainvoke({
            "query": query,
            "sections": sections_text
        })
        
        # Parse and return the JSON response
        return json.loads(response.content)

    def analyze_sections(self, query: str, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze document sections based on the query.
        
        Args:
            query: The user's query
            sections: List of document sections with titles and line numbers
            
        Returns:
            Dict containing main section and supplementary sections
        """
        print(f"\nDebug - SectionFinder received {len(sections)} sections")
        if sections:
            print(f"First section title: {sections[0].get('title')}")
        
        # Check if we have meaningful sections to work with
        if not sections or (len(sections) == 1 and sections[0].get('title') == 'Document Total'):
            # No meaningful sections found, use the entire document
            print("\nDebug - No meaningful sections found, using entire document")
            total_lines = 0
            for section in sections:
                end_line = section.get('end_line', 0)
                if end_line > total_lines:
                    total_lines = end_line
            
            return {
                "main": {
                    "title": "Entire Document",
                    "lines": f"0-{total_lines}"
                },
                "supplement": []
            }
        
        # Format sections for the prompt
        sections_text = ""
        for section in sections:
            sections_text += f"Title: {section['title']}\n"
            # Format line numbers as start-end
            start_line = section.get('start_line', 0)
            end_line = section.get('end_line', 0)
            sections_text += f"Lines: {start_line}-{end_line}\n"
            
            # Limit content length to avoid token limits
            content = section.get('content', '')
            if content and len(content) > 500:
                content = content[:500] + "..."
            
            sections_text += f"Content:\n{content}\n\n"
        
        print("\nDebug - Formatted Sections Text:")
        print(sections_text)
        
        # Run the analysis
        prompt = self.section_prompt.format(
            query=query,
            sections=sections_text
        )
        
        print("\nDebug - Generated Prompt:")
        print(prompt)
        
        response = self.llm.invoke(prompt)
        
        print("\nDebug - LLM Response (Raw):")
        print(response.content)
        
        # Parse and return the results
        try:
            # Extract JSON from the response
            response_text = response.content.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]  # Remove ```json and ``` markers
            elif response_text.startswith('{'):
                pass  # Already JSON format
            else:
                # Try to find JSON object in the text
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    response_text = response_text[start:end]
                else:
                    raise ValueError("No valid JSON found in response")
                    
            result = json.loads(response_text)
            
            print("\nDebug - Parsed Result:")
            print(json.dumps(result, indent=2))
            
            # Validate the result structure
            if not isinstance(result, dict) or 'main' not in result or 'supplement' not in result:
                raise ValueError("Invalid response format")
            
            # Ensure the main section has required fields
            if not isinstance(result['main'], dict) or 'title' not in result['main'] or 'lines' not in result['main']:
                raise ValueError("Main section missing required fields")
            
            # Ensure each supplement section has required fields
            for supp in result.get('supplement', []):
                if not isinstance(supp, dict) or 'title' not in supp or 'lines' not in supp:
                    raise ValueError("Supplement section missing required fields")
                
            return result
        except Exception as e:
            print(f"Error parsing response: {str(e)}")
            print(f"Raw response: {response.content}")
            return {
                "main": {"title": "Error", "lines": "0-0"},
                "supplement": []
            }
