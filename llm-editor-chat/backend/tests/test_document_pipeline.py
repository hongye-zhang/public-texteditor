import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import json

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the services to test
from app.services.document_pipeline_service import DocumentPipelineService
from document_pipeline import DocumentPipeline

class TestDocumentPipeline(unittest.TestCase):
    """Test the document pipeline integration"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary test file
        self.test_content = """# Test Document
        
## Introduction
This is a test document for pipeline integration.

## Methods
We use various methods to test the pipeline.

## Results
The results show that the pipeline works correctly.
"""
        self.test_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_test_doc.md")
        with open(self.test_file_path, "w", encoding="utf-8") as f:
            f.write(self.test_content)
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove temporary test file
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
    
    def test_service_initialization(self):
        """Test that the service initializes correctly"""
        service = DocumentPipelineService.get_instance()
        self.assertIsNotNone(service)
        self.assertIsNotNone(service._pipeline)
        self.assertIsInstance(service._pipeline, DocumentPipeline)
    
    def test_should_use_pipeline(self):
        """Test the logic for determining when to use the pipeline"""
        service = DocumentPipelineService.get_instance()
        
        # Should use pipeline: editing request with content but no selection
        self.assertTrue(service.should_use_pipeline(
            "Edit the introduction section", 
            "Some document content", 
            None
        ))
        
        # Should not use pipeline: has selection
        self.assertFalse(service.should_use_pipeline(
            "Edit this text", 
            "Some document content", 
            "Selected text"
        ))
        
        # Should not use pipeline: no editing intent
        self.assertFalse(service.should_use_pipeline(
            "What is this document about?", 
            "Some document content", 
            None
        ))
    
    @patch('document_pipeline.DocumentPipeline.process_document')
    def test_process_document(self, mock_process):
        """Test document processing with mocked pipeline"""
        # Set up mock
        mock_process.return_value = None
        
        # Call the service
        service = DocumentPipelineService.get_instance()
        result = service.process_document(self.test_file_path, "Add a new paragraph to the Methods section")
        
        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["prompt"], "Add a new paragraph to the Methods section")
        
        # Verify the mock was called correctly
        mock_process.assert_called_once_with(self.test_file_path, "Add a new paragraph to the Methods section")
    
    def test_save_temp_file(self):
        """Test saving content to a temporary file"""
        service = DocumentPipelineService.get_instance()
        content = "Test content for temporary file"
        
        file_path, success, message = service.save_temp_file(content)
        
        # Verify the result
        self.assertTrue(success)
        self.assertTrue(os.path.exists(file_path))
        
        # Verify the file content
        with open(file_path, "r", encoding="utf-8") as f:
            saved_content = f.read()
        self.assertEqual(saved_content, content)
        
        # Clean up
        os.remove(file_path)

if __name__ == "__main__":
    unittest.main()
