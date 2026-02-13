import unittest
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.features.document_structure.services.document_analyzer import DocumentStructureAnalyzer  # Updated import path

class TestDocumentAnalyzer(unittest.TestCase):    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Initialize with a dummy API key for testing
        self.analyzer = DocumentStructureAnalyzer(api_key="dummy_key")
    
    def test_analyze_html_basic_structure(self):
        """Test basic HTML structure parsing"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Document</title>
        </head>
        <body>
            <h1>Main Title</h1>
            <p>First paragraph.</p>
            <h2>Subsection</h2>
            <p>Second paragraph.</p>
        </body>
        </html>
        """
        
        result = self.analyzer.analyze_html(html)
        
        # Check root node
        self.assertEqual(result["type"], "document")
        self.assertEqual(result["level"], 0)
        self.assertIn("children", result)
        
        # The first child should be the html element
        self.assertGreaterEqual(len(result["children"]), 1)
        html_node = result["children"][0]
        self.assertEqual(html_node["type"], "html")
        
        # The html node should have children (head and body)
        self.assertGreaterEqual(len(html_node["children"]), 1)
        
        # Find the body node
        body_node = None
        for child in html_node["children"]:
            if child["type"] == "body":
                body_node = child
                break
                
        self.assertIsNotNone(body_node, "Body node not found")
        
        # Check first child in body (h1)
        self.assertGreaterEqual(len(body_node["children"]), 1)
        h1_node = body_node["children"][0]
        self.assertEqual(h1_node["type"], "h1")
        self.assertEqual(h1_node["content"].strip(), "Main Title")
        self.assertEqual(h1_node["level"], 1)
        
        # Check paragraph after h1
        self.assertGreaterEqual(len(body_node["children"]), 2)
        p1_node = body_node["children"][1]
        self.assertEqual(p1_node["type"], "p")
        self.assertEqual(p1_node["content"].strip(), "First paragraph.")
        self.assertEqual(p1_node["level"], 1)
        
        # Check h2
        self.assertGreaterEqual(len(body_node["children"]), 3)
        h2_node = body_node["children"][2]
        self.assertEqual(h2_node["type"], "h2")
        self.assertEqual(h2_node["content"].strip(), "Subsection")
        self.assertEqual(h2_node["level"], 1)
    
    def test_analyze_html_nested_structure(self):
        """Test nested HTML structure"""
        html = """
        <div>
            <h1>Main Title</h1>
            <div class="section">
                <h2>Section Title</h2>
                <p>Section content.</p>
            </div>
        </div>
        """
        
        result = self.analyzer.analyze_html(html)
        
        # The first child should be the outer div
        self.assertGreaterEqual(len(result["children"]), 1)
        outer_div = result["children"][0]
        self.assertEqual(outer_div["type"], "div")
        
        # The outer div should have two children: h1 and inner div
        self.assertGreaterEqual(len(outer_div["children"]), 2)
        
        # Check h1
        h1_node = outer_div["children"][0]
        self.assertEqual(h1_node["type"], "h1")
        self.assertEqual(h1_node["content"].strip(), "Main Title")
        
        # Check nested div
        inner_div = outer_div["children"][1]
        self.assertEqual(inner_div["type"], "div")
        
        # Check h2 inside inner div
        self.assertGreaterEqual(len(inner_div["children"]), 1)
        h2_node = inner_div["children"][0]
        self.assertEqual(h2_node["type"], "h2")
        self.assertEqual(h2_node["content"].strip(), "Section Title")
        self.assertEqual(div_node["children"][1]["type"], "p")
    
    def test_analyze_html_with_positions(self):
        """Test that position information is correctly captured"""
        html = """<h1>Title</h1><p>Content</p>"""
        
        result = self.analyzer.analyze_html(html)
        
        # Check positions exist and are valid
        h1_node = result["children"][0]
        self.assertIn("position", h1_node)
        self.assertIsInstance(h1_node["position"]["start"], int)
        self.assertIsInstance(h1_node["position"]["end"], int)
        self.assertLess(h1_node["position"]["start"], h1_node["position"]["end"])
    
    def test_analyze_html_empty(self):
        """Test with empty HTML"""
        result = self.analyzer.analyze_html("")
        self.assertEqual(result["type"], "document")
        self.assertEqual(len(result["children"]), 0)
    
    def test_analyze_html_invalid(self):
        """Test with invalid HTML"""
        result = self.analyzer.analyze_html("<invalid<markup")
        self.assertEqual(result["type"], "document")  # Should still return a document node

if __name__ == "__main__":
    unittest.main()
