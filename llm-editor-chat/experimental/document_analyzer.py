from docx import Document
from typing import Dict, Any, List, Optional
import json
import re
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.cache import InMemoryCache
from langchain_core.runnables import RunnablePassthrough
import hashlib
from dataclasses import dataclass
from datetime import datetime
import sys
import os

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
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError("OPENAI_API_KEY environment variable not found")
            
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
                        continue
                summary = " ".join(summaries)
            else:
                result = chain.invoke({
                    "text": text,
                    "max_words": max_words
                })
                summary = result.content
                
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
            return ""
    
    def _parse_markdown_heading(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a markdown heading line
        
        Args:
            line: Line to parse
            
        Returns:
            Dictionary with heading info or None if not a heading
        """
        if not line.startswith("#"):
            return None
            
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
        
        lines = markdown_text.split("\n")
        total_lines = len(lines)
        
        # Find all sections at the root level
        root_sections, _ = self._find_child_sections(lines, 0, 0)
        
        # Create root section if there is content
        root_section = {
            "title": "Document Total",
            "type": "",
            "start_line": 0,
            "end_line": total_lines - 1,
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
    # Example usage
    analyzer = DocumentStructureAnalyzer()
    print("Initializing document analyzer...")
    
    # Analyze markdown text
    markdown_text = """
# Background

In 1809, Europe was embroiled in warfare, pitting revolutionary France against a series of coalitions in the Coalition Wars almost continuously since 1792. A brief period of peace followed the March 1802 Treaty of Amiens before British-French relations deteriorated, leading to the War of the Third Coalition in May 1803.

Britain was joined in their coalition by Sweden in 1804 and Russia and Austria in 1805. In August 1805, the 200,000-strong French Grande Armée invaded the German states, hoping to defeat Austria before Russian forces could intervene. The French emperor Napoleon successfully wheeled his army into the Austrian rear and defeated them at the Battle of Ulm, fought from 15 to 20 October. The Austrian capital, Vienna, was captured in November and a Russo-Austrian army was decisively defeated at the 2 December Battle of Austerlitz.

Austerlitz incited a major shift in the European balance of power. Prussia felt threatened in the region and, alongside Russia, declared war against France in the 1806 War of the Fourth Coalition. After French victories at the Battle of Jena-Auerstadt on 14 October, France occupied the Prussian capital, Berlin. France invaded Poland in November, where Russian forces were stationed, and occupied Warsaw. Russian and French armies fought in February 1807 at the violent, indecisive Battle of Eylau. The action in Poland culminated on 14 June 1807 when the French defeated Russia at the Battle of Friedland.

The resulting Treaty of Tilsit in July left France as the dominant power in Western Europe, with many client states including the Duchy of Warsaw. This weakened Prussia and allowed Russia to expand into Finland and South-Eastern Europe.

## Peninsular War

In 1807, France tried to force Portugal to join the Continental System, a commercial embargo against Britain. When the Portuguese prince regent, John, refused to join, Napoleon sent General Junot to invade Portugal in 1807, resulting in the six year Peninsular War. The war weakened the French empire's military, particularly after Spanish forces and civilians rebelled against France after Napoleon overthrew the Spanish king. After the French defeat at the Battle of Bailén, Napoleon took command of the French forces, defeating the Spanish armies before returning to France.

Jean-de-Dieu Soult drove the British out of Spain in the Battle of Corunna in January 1809.

In the beginning of 1809, the French client kingdom of Spain, ruled by Napoleon's brother Joseph Bonaparte, controlled much of Spain and northern Portugal. British and Portuguese forces under Arthur Wellesley launched new offensives from Spring 1809. Spanish regular armies including those led by General Joaquín Blake continued to fight and guerrilla activity in the countryside made French operations hazardous. A significant French presence, numbering 250,000 in June 1809, remained in the peninsula throughout the War of the Fifth Coalition.

The Napoleonic occupation of France's own ally Spain persuaded many in Austria that Napoleon could not be trusted and declaring war was the only way to prevent him from destroying the Habsburg monarchy. The Spanish guerrillas inspired popular resistance against Napoleon, and the Austrians hoped that French preoccupation in Spain would make it easier to defeat France.

## Austria plans for war

Austria hoped Prussia would assist them in a war with France but a letter from Prussian minister Baron von Stein discussing the negotiations was intercepted by French agents and published in the Le Moniteur Universel on 8 September. Napoleon confiscated Stein's holdings in Westphalia and pressured King Frederick William III into dismissing him, and Stein fled into exile in Austria.

On the same day that Stein was compromised the Convention of Paris agreed a timetable for the withdrawal of foreign troops from Prussia, where French garrisons had been in place since the end of the War of the Fourth Coalition. The withdrawal was contingent on the payment of heavy reparations, totalling 140 million francs, over 30 months. The Prussian Army was also limited in size to 42,000 men, one sixth of its pre-war total. The convention severely restricted the ability of the Prussian state to wage war.

France withdrew 108,000 troops from Germany, more than half their strength there, to reinforce the French armies in Spain in October 1808. This lent support to Stadion's pro-war faction at the Austrian court. Stadion recalled Klemens von Metternich, his ambassador to Paris, to convince others to support his plan and by December 1808 Emperor Francis I was persuaded to support the war.

Austria and Prussia requested that Britain fund their military campaigns and requested a British military expedition to Germany. In April 1809 the British treasury supplied £20,000 in credit to Prussia, with additional funds promised if Prussia opened hostilities with France. Austria received £250,000 in silver, with a further £1 million promised for future expenses. Britain refused to land troops in Germany but promised an expedition to the low countries and to renew their campaign in Spain.
"""
doc_structure = analyzer.analyze_docx(markdown_text)

# Or analyze a docx file
# doc_structure = analyzer.analyze_docx("", docx_path="sample.docx")

# Get complete document structure (default view)
structure = analyzer.get_document_structure(doc_structure)

# Get position-based context view if needed
context = analyzer.get_position_context(doc_structure, 5, window_size=2)
print(json.dumps(structure, indent=2, ensure_ascii=False))
