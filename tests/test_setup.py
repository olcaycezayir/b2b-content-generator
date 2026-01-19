"""
Basic setup tests to verify project structure and dependencies.
"""

import pytest
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test that all required modules can be imported."""
    try:
        import streamlit
        import openai
        import pandas
        import dotenv
        import hypothesis
        import PIL
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import required dependency: {e}")


def test_project_structure():
    """Test that all required project files exist."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    required_files = [
        'ui.py',
        'content_generator.py',
        'llm_service.py',
        'csv_processor.py',
        'utils.py',
        'requirements.txt',
        '.env.example',
        'README.md',
        '.gitignore',
        'setup_instructions.md'
    ]
    
    for file_name in required_files:
        file_path = os.path.join(project_root, file_name)
        assert os.path.exists(file_path), f"Required file {file_name} not found"


def test_module_imports():
    """Test that project modules can be imported."""
    try:
        import ui
        import content_generator
        import llm_service
        import csv_processor
        import utils
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import project module: {e}")


def test_data_classes():
    """Test that data classes are properly defined."""
    from content_generator import ProductInput, ProductContent
    from utils import ValidationResult, ProcessingProgress
    
    # Test ProductInput
    product_input = ProductInput(name="Test Product")
    assert product_input.name == "Test Product"
    assert product_input.additional_attributes == {}
    
    # Test ProductContent
    content = ProductContent(
        title="Test Title",
        description=" ".join(["word"] * 150),  # 150 words
        hashtags=["#test1", "#test2", "#test3", "#test4", "#test5"]
    )
    validation_result = content.validate()
    assert validation_result.is_valid == True
    
    # Test ValidationResult
    result = ValidationResult(is_valid=True, errors=[])
    assert result.is_valid == True
    assert result.errors == []
    
    # Test ProcessingProgress
    progress = ProcessingProgress(current=5, total=10, status="processing")
    assert progress.current == 5
    assert progress.total == 10


if __name__ == "__main__":
    pytest.main([__file__])