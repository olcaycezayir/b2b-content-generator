"""
Integration tests for ContentGenerator with real dependencies.

Tests the ContentGenerator with actual LLMService and DataValidator instances
to ensure proper integration.
"""

import pytest
import os
from unittest.mock import Mock, patch

from content_generator import ContentGenerator
from llm_service import LLMService
from utils import DataValidator, ConfigurationManager, ProductInput


class TestContentGeneratorIntegration:
    """Integration test cases for ContentGenerator."""
    
    @pytest.fixture
    def config_manager(self):
        """Create a mock configuration manager for testing."""
        mock_config = Mock(spec=ConfigurationManager)
        mock_config.validate_api_key.return_value = True
        mock_config.get_int_config.return_value = 3
        mock_config.get_float_config.return_value = 1.0
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_config.get_openai_client.return_value = mock_client
        
        return mock_config
    
    @pytest.fixture
    def data_validator(self):
        """Create real DataValidator instance."""
        return DataValidator()
    
    @pytest.fixture
    def llm_service(self, config_manager):
        """Create LLMService with mocked OpenAI client."""
        with patch('llm_service.OPENAI_AVAILABLE', True):
            service = LLMService(config_manager)
            return service
    
    @pytest.fixture
    def content_generator(self, llm_service, data_validator):
        """Create ContentGenerator with real dependencies."""
        return ContentGenerator(llm_service, data_validator)
    
    def test_content_generator_initialization(self, content_generator, llm_service, data_validator):
        """Test that ContentGenerator initializes properly with real dependencies."""
        assert content_generator.llm_service == llm_service
        assert content_generator.validator == data_validator
        assert hasattr(content_generator, 'TONE_PROFILES')
        assert len(content_generator.TONE_PROFILES) > 0
    
    def test_product_input_validation_integration(self, content_generator):
        """Test product input validation with real DataValidator."""
        # Valid input
        valid_input = ProductInput(name="Test Product")
        validation_result = content_generator.validator.validate_product_input(valid_input)
        assert validation_result.is_valid
        
        # Invalid input (empty)
        invalid_input = ProductInput()
        validation_result = content_generator.validator.validate_product_input(invalid_input)
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
    
    def test_text_sanitization_integration(self, content_generator):
        """Test text sanitization with real DataValidator."""
        # Test with potentially dangerous input
        dangerous_input = "<script>alert('xss')</script>Product Name"
        sanitized = content_generator.validator.sanitize_text_input(dangerous_input)
        
        assert "<script>" not in sanitized
        assert "Product Name" in sanitized
    
    @patch('llm_service.OpenAI')
    def test_generate_content_with_mocked_api(self, mock_openai_class, content_generator):
        """Test content generation with mocked OpenAI API response."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '''
        {
            "title": "Premium Test Product - High Quality",
            "description": "This is a comprehensive test product description that contains more than one hundred words to meet the minimum requirement for content generation. The product features advanced technology and premium materials that deliver exceptional performance and reliability. Customers will appreciate the attention to detail and the innovative design that sets this product apart from competitors. With its durable construction and user-friendly interface, this product is perfect for both beginners and experienced users. The comprehensive warranty and customer support ensure complete satisfaction with your purchase.",
            "hashtags": ["#test", "#product", "#premium", "#quality", "#innovation"]
        }
        '''
        mock_response.choices[0].finish_reason = 'stop'
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 150
        
        # Setup mock client
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Update the service's client and mock validation
        content_generator.llm_service.client = mock_client
        content_generator.llm_service._validate_api_response = Mock(return_value=True)
        
        # Test content generation
        product_input = ProductInput(name="Test Product")
        result = content_generator.generate_single_product_content(product_input, 'professional')
        
        # Verify result
        assert result.title == "Premium Test Product - High Quality"
        assert len(result.description.split()) >= 100
        assert len(result.hashtags) == 5
        assert all(hashtag.startswith('#') for hashtag in result.hashtags)
        
        # Verify API was called
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['model'] == 'gpt-4o'
        assert 'professional' in call_args[1]['messages'][1]['content'].lower()
    
    def test_tone_application_in_prompt(self, content_generator):
        """Test that different tones are properly applied in prompts."""
        product_info = "Product Name: Test Product"
        
        # Test different tones
        tones = ['professional', 'casual', 'luxury', 'energetic', 'minimalist']
        
        for tone in tones:
            prompt = content_generator._create_prompt(product_info, tone)
            
            # Verify tone is mentioned in prompt
            assert tone.lower() in prompt.lower()
            
            # Verify tone profile characteristics are included
            tone_profile = content_generator.TONE_PROFILES[tone]
            assert tone_profile['description'].lower() in prompt.lower()
    
    def test_content_validation_integration(self, content_generator):
        """Test content validation with real ProductContent validation."""
        from utils import ProductContent
        
        # Valid content
        valid_content = ProductContent(
            title="Valid Product Title",
            description=" ".join(["word"] * 150),  # 150 words
            hashtags=["#test", "#product", "#example", "#demo", "#sample"]
        )
        
        validation_result = valid_content.validate()
        assert validation_result.is_valid
        
        # Invalid content (title too long)
        invalid_content = ProductContent(
            title="This is a very long title that exceeds the sixty character limit",
            description=" ".join(["word"] * 150),
            hashtags=["#test", "#product", "#example", "#demo", "#sample"]
        )
        
        validation_result = invalid_content.validate()
        assert not validation_result.is_valid
        assert any("60 characters" in error for error in validation_result.errors)
    
    def test_error_handling_integration(self, content_generator):
        """Test error handling with real validation errors."""
        # Test with invalid product input
        invalid_input = ProductInput()  # No name or image
        
        with pytest.raises(ValueError, match="Invalid product input"):
            content_generator.generate_single_product_content(invalid_input, 'professional')
    
    def test_available_tones_integration(self, content_generator):
        """Test getting available tones with real implementation."""
        tones = content_generator.get_available_tones()
        
        assert isinstance(tones, dict)
        assert len(tones) >= 5  # Should have at least 5 tone options
        
        # Verify expected tones are present
        expected_tones = ['professional', 'casual', 'luxury', 'energetic', 'minimalist']
        for tone in expected_tones:
            assert tone in tones
            assert isinstance(tones[tone], str)
            assert len(tones[tone]) > 0
    
    def test_product_info_extraction_integration(self, content_generator):
        """Test product info extraction with real sanitization."""
        # Test with complex product input
        product_input = ProductInput(
            name="<b>Premium Product</b> with Special Characters & Symbols",
            image_data=b"fake_image_data",
            additional_attributes={
                "brand": "Test Brand",
                "price": "$99.99",
                "category": "Electronics & Gadgets"
            }
        )
        
        product_info = content_generator._extract_product_info(product_input)
        
        # Verify sanitization occurred
        assert "<b>" not in product_info
        assert "Premium Product" in product_info
        assert "Test Brand" in product_info
        assert "$99.99" in product_info
        assert "Image: Product image provided" in product_info