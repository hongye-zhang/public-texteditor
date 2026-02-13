from docx import Document
from typing import Dict, Any, List, Optional, Tuple
import json
import re
from bs4 import BeautifulSoup, Tag, NavigableString
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.cache import InMemoryCache
from langchain_core.runnables import RunnablePassthrough
import hashlib
from dataclasses import dataclass
from datetime import datetime
import sys
import traceback

class SummaryCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[str]:
        """Get a cached summary if it exists."""
        if key in self._cache:
            return self._cache[key]["summary"]
        return None
    
    def put(self, key: str, entry: Dict[str, Any]) -> None:
        """Store a summary in the cache."""
        self._cache[key] = entry

class DocumentStructureAnalyzer:
    """Analyzes document structure from markdown or docx files"""
    
    def __init__(self, api_key: str = None):
        """Initialize with your API key."""
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("API key is required")
            
        self.current_line = 0
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model_name="gpt-3.5-turbo",
            temperature=0.3
        )
        
        # Initialize cache
        self.cache = SummaryCache()
        
        # Create different summarization chains for different content types
        self.summary_chains = {}
        if self.llm:
            self._initialize_summary_chains()
        
        # Text splitter for longer documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
    
    def _initialize_summary_chains(self):
        """Initialize different summarization chains for different content types."""
        prompts = {
            "heading": PromptTemplate(
                template="Create a very concise label for this heading in {max_words} words:\n\n{text}",
                input_variables=["text", "max_words"]
            ),
            "technical": PromptTemplate(
                template="Summarize this technical content, preserving key technical details in {max_words} words:\n\n{text}",
                input_variables=["text", "max_words"]
            ),
            "narrative": PromptTemplate(
                template="Create a concise narrative summary in {max_words} words, focusing on key plot points:\n\n{text}",
                input_variables=["text", "max_words"]
            ),
            "list": PromptTemplate(
                template="Summarize this list into {max_words} words, preserving the key items:\n\n{text}",
                input_variables=["text", "max_words"]
            )
        }
        
        for content_type, prompt in prompts.items():
            # Create a runnable sequence: prompt | llm
            self.summary_chains[content_type] = prompt | self.llm
    
    def _detect_content_type(self, text: str) -> str:
        """
        Detect the type of content based on text characteristics.
        Returns a string value for JSON serialization.
        """
        # Check if it's a list (bullet points or numbered)
        if any(line.strip().startswith(('•', '-', '*', '1.', '2.')) for line in text.split('\n')):
            return "list"
            
        # Check if it's technical (contains technical indicators)
        technical_indicators = {'code', 'function', 'class', 'method', 'api', 'data', 'algorithm'}
        if any(indicator in text.lower() for indicator in technical_indicators):
            return "technical"
            
        # For headings, return heading type
        if len(text.split()) <= 10 and not any(char in text for char in '.,:;()'):
            return "heading"
            
        # Default to narrative for regular paragraphs
        return "narrative"
    
    def _get_cache_key(self, text: str, content_type: str, max_words: int) -> str:
        """Generate a cache key based on content and parameters."""
        content_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{content_hash}_{content_type}_{max_words}"
    
    def _generate_summary(self, text: str, max_words: int = 15) -> str:
        """Generate a concise summary using appropriate strategy and caching."""
        if not text or not self.llm:
            return ""
            
        # Detect content type
        content_type = self._detect_content_type(text)
        
        # Check cache first
        cache_key = self._get_cache_key(text, content_type, max_words)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        try:
            # Get appropriate chain for content type
            chain = self.summary_chains.get(content_type)
            if not chain:
                # Fallback to narrative if no specific chain
                chain = self.summary_chains["narrative"]
                
            # Split long text if needed
            if len(text) > 1000:
                chunks = self.text_splitter.split_text(text)
                summaries = []
                for chunk in chunks:
                    try:
                        result = chain.invoke({
                            "text": chunk,
                            "max_words": max_words // len(chunks)
                        })
                        summaries.append(result.content)
                    except Exception as e:
                        print(f"Error generating summary for chunk: {e}")
                        traceback.print_exc()
                        continue
                summary = " ".join(summaries)
            else:
                try:
                    result = chain.invoke({
                        "text": text,
                        "max_words": max_words
                    })
                    summary = result.content
                except Exception as e:
                    print(f"Error invoking LLM for summary: {e}")
                    traceback.print_exc()
                    return ""
                
            # Clean and format summary
            summary = summary.strip().replace("\n", " ")
            
            # Cache the result
            self.cache.put(cache_key, {
                "summary": summary,
                "timestamp": datetime.now().isoformat()
            })
            
            return summary
        except Exception as e:
            print(f"Error in summary generation: {e}")
            traceback.print_exc()
            return ""
    
    def _parse_markdown_heading(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a markdown heading line
        
        Args:
            line: Line to parse
            
        Returns:
            Dictionary with heading info or None if not a heading
        """
        # Check for ATX-style headings (# Heading)
        if line.startswith("#"):
            # Count heading level
            level = 0
            for char in line:
                if char == "#":
                    level += 1
                else:
                    break
                    
            # Extract heading text
            text = line[level:].strip()
            if not text:
                return None
                
            return {
                "text": text,
                "level": level
            }
        
        # Check for bold text as potential section headers
        bold_pattern = r'^\*\*(.*?)\*\*$'
        match = re.match(bold_pattern, line.strip())
        if match:
            return {
                "text": match.group(1),
                "level": 3  # Treat bold text as level 3 heading
            }
            
        # Check for other potential section indicators
        if line.strip() and line.strip().isupper() and len(line.strip()) < 50:
            # All uppercase lines might be section headers
            return {
                "text": line.strip(),
                "level": 3
            }
            
        return None
    
    def _parse_markdown_paragraph(self, lines: List[str], start_idx: int) -> Optional[Dict[str, Any]]:
        """Parse markdown paragraph lines"""
        text = []
        i = start_idx
        
        while i < len(lines) and lines[i].strip():
            text.append(lines[i].strip())
            i += 1
            
        content = " ".join(text)
        content_type = self._detect_content_type(content)
        summary = self._generate_summary(content) if self.llm else ""
        
        return {
            "type": "paragraph",
            "content": content,
            "content_type": content_type,
            "summary": summary,
            "start_line": start_idx,
            "end_line": i - 1
        }, i
    
    def _find_child_sections(self, lines: List[str], current_level: int, start_idx: int) -> tuple[List[Dict[str, Any]], int]:
        """
        Find child sections at the current heading level
        
        Args:
            lines: List of document lines
            current_level: Current heading level
            start_idx: Starting line index
            
        Returns:
            Tuple of (list of child sections, next line index)
        """
        sections = []
        idx = start_idx
        
        while idx < len(lines):
            line = lines[idx].strip()
            
            if line.startswith("#"):
                heading_info = self._parse_markdown_heading(line)
                if not heading_info:
                    idx += 1
                    continue
                    
                # If we find a heading at current or higher level, we're done with this section
                if heading_info["level"] <= current_level:
                    break
                    
                # If we find a heading one level deeper, create a new section
                if heading_info["level"] == current_level + 1:
                    section = {
                        "title": heading_info["text"],
                        "level": heading_info["level"],
                        "type": "heading",
                        "start_line": idx,
                        "summary": self._generate_summary(heading_info["text"], max_words=10) if self.llm else ""
                    }
                    
                    # Collect content until next heading
                    content_lines = []
                    next_idx = idx + 1
                    while next_idx < len(lines):
                        next_line = lines[next_idx].strip()
                        if next_line.startswith("#"):
                            next_heading = self._parse_markdown_heading(next_line)
                            if next_heading and next_heading["level"] <= heading_info["level"]:
                                break
                        content_lines.append(lines[next_idx])
                        next_idx += 1
                    
                    if content_lines:
                        content = "\n".join(content_lines)
                        section["content"] = content
                        section["content_type"] = self._detect_content_type(content)
                        section["summary"] = self._generate_summary(content) if self.llm else ""
                    
                    # Find child sections
                    child_sections, new_idx = self._find_child_sections(lines, heading_info["level"], idx + 1)
                    if child_sections:
                        section["children"] = child_sections
                        section["end_line"] = child_sections[-1]["end_line"]
                    else:
                        section["end_line"] = next_idx - 1 if content_lines else idx
                    
                    sections.append(section)
                    idx = new_idx
                    continue
            
            idx += 1
        
        return sections, idx

    def _get_element_position(self, element: Tag) -> Dict[str, int]:
        """Get the start and end position of an HTML element"""
        if not element or not element.sourceline:
            return {"start": 0, "end": 0}
            
        start_pos = element.sourceline - 1  # Convert to 0-based
        end_pos = start_pos + len(str(element).split('\n'))
        return {"start": start_pos, "end": end_pos}

    def _parse_html_node(self, element: Tag, parent_level: int = 0) -> List[Dict]:
        """Recursively parse HTML nodes into a tree structure"""
        result = []
        
        for child in element.children:
            if not isinstance(child, Tag):
                if isinstance(child, NavigableString) and child.strip():
                    # Handle text nodes that are direct children of the current element
                    node = {
                        "type": "paragraph",
                        "level": parent_level + 1,
                        "content": str(child).strip(),
                        "position": {
                            "start": child.sourceline - 1 if hasattr(child, 'sourceline') else 0,
                            "end": (child.sourceline - 1 if hasattr(child, 'sourceline') else 0) + 1
                        },
                        "children": []
                    }
                    result.append(node)
                continue
                
            # Skip script and style tags
            if child.name in ['script', 'style']:
                continue
                
            # Determine node type and level
            node_type = child.name
            level = parent_level + 1
            
            # Handle headings
            if child.name.startswith('h') and child.name[1:].isdigit():
                level = int(child.name[1:])
                node_type = f"h{level}"
            
            # Create node
            node = {
                "type": node_type,
                "level": level,
                "content": child.get_text().strip(),
                "position": self._get_element_position(child),
                "children": []
            }
            
            # Process child nodes
            child_nodes = self._parse_html_node(child, level)
            if child_nodes:
                node["children"] = child_nodes
            
            result.append(node)
            
        return result

    def analyze_html(self, html_text: str) -> Dict[str, Any]:
        """
        Analyze HTML document structure and return a tree of nodes
        
        Args:
            html_text: HTML text to analyze
            
        Returns:
            Dict containing document structure as a tree of nodes
        """
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # Create a root node
            root = {
                "type": "document",
                "level": 0,
                "content": "",
                "position": {"start": 0, "end": 0},
                "children": []
            }
            
            # Parse the document body or use the root element
            body = soup.find('body')
            if body:
                root["children"] = self._parse_html_node(body, 0)
            else:
                root["children"] = self._parse_html_node(soup, 0)
            
            return root
            
        except Exception as e:
            print(f"Error analyzing HTML: {str(e)}")
            return {
                "type": "error",
                "level": 0,
                "content": f"Error analyzing document: {str(e)}",
                "position": {"start": 0, "end": 0},
                "children": []
            }
    
    def analyze_docx(self, markdown_text: str, docx_path: str = None) -> Dict[str, Any]:
        """
        Analyze document structure from markdown text or docx file
        
        Args:
            markdown_text: Markdown text to analyze
            docx_path: Optional path to docx file
            
        Returns:
            Document structure with sections
        """
        if docx_path:
            doc = Document(docx_path)
            markdown_text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        
        # Ensure we have content to analyze
        if not markdown_text or markdown_text.strip() == "":
            print("Warning: Empty markdown text provided for analysis")
            markdown_text = "Empty document"
        
        lines = markdown_text.split("\n")
        total_lines = len(lines)
        
        print(f"Debug - Document has {total_lines} lines")
        
        # Find all sections at the root level
        root_sections, _ = self._find_child_sections(lines, 0, 0)
        
        # Create root section if there is content
        root_section = {
            "title": "Document Total",
            "type": "",
            "start_line": 0,
            "end_line": max(0, total_lines - 1),  # Ensure end_line is at least 0
            "content_type": "",
            "summary": self._generate_summary(markdown_text) if self.llm else "",
            "children": root_sections
        }
        
        # Add position information to all sections
        def add_positions(sections):
            for section in sections:
                if "children" in section:
                    add_positions(section["children"])
        
        add_positions(root_sections)
        
        return {
            "sections": [root_section],
            "total_lines": total_lines
        }

    # add a function to get the document structure from a file path
    def analyze_docx_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze document structure from a file path
        
        Args:
            file_path: Path to the document to analyze
            
        Returns:
            Dict containing document structure and analysis
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
        
        return self.analyze_document(markdown_text)
    
    def get_document_structure(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the complete document structure tree.
        Args:
            structure: The document structure from analyze_docx
        Returns:
            Document structure tree with headings, content, and line information
        """
        def process_section(section: Dict[str, Any]):
            result = {
                "title": section.get("title", ""),
                "type": section.get("type", ""),
                "summary": section.get("summary", ""),
                "content_type": section.get("content_type", ""),
                "start_line": section.get("start_line", 0),
                "end_line": section.get("end_line", 0)
            }
            
            if "children" in section and section["children"]:
                result["children"] = [process_section(child) for child in section["children"]]
                
            return result
            
        sections = [process_section(section) for section in structure["sections"]]
        return {
            "sections": sections,
            "total_lines": structure.get("total_lines", 0)
        }

    def get_position_context(self, structure: Dict[str, Any], position: int, window_size: int = 2) -> Dict[str, Any]:
        """
        Get a windowed view of content around a specific position.
        Args:
            structure: The document structure
            position: The position to look for
            window_size: Number of items to include before and after
        Returns:
            Context window with before/current/after sections and path to position
        """
        def find_in_sections(sections: List[Dict[str, Any]], pos: int) -> Optional[Dict[str, Any]]:
            """Find section containing the given position and return context"""
            # Flatten sections into a list for windowing
            flat_sections = []
            
            def flatten_section(section: Dict[str, Any], path: List[str] = None):
                if path is None:
                    path = []
                
                current_path = path + [section["title"]]
                section_copy = section.copy()
                section_copy["path"] = current_path
                
                # Add type if not present
                if "type" not in section_copy:
                    section_copy["type"] = "heading"
                
                flat_sections.append(section_copy)
                
                if "children" in section:
                    for child in section["children"]:
                        flatten_section(child, current_path)
            
            # Flatten all sections
            for section in sections:
                flatten_section(section)
            
            # Find the section containing our position
            target_idx = None
            for idx, section in enumerate(flat_sections):
                start = section.get("start_line", 0)
                end = section.get("end_line", 0)
                if start <= pos <= end:
                    target_idx = idx
                    break
            
            if target_idx is None:
                return None
            
            # Get window of sections
            start_idx = max(0, target_idx - window_size)
            end_idx = min(len(flat_sections), target_idx + window_size + 1)
            
            return {
                "before": [s for s in flat_sections[start_idx:target_idx]],
                "current": flat_sections[target_idx],
                "after": [s for s in flat_sections[target_idx + 1:end_idx]],
                "path": flat_sections[target_idx]["path"]
            }
        
        return find_in_sections(structure["sections"], position)

if __name__ == "__main__":
    print("Run test_pipeline.py to test the document analyzer functionality")
