"""
Unit tests for ContentGenerator class.

Tests the core business logic for generating product content
using AI services.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock
import json

from content_generator import ContentGenerator
from utils import ProductInput, ProductContent, ValidationResult, DataValidator
from llm_service import LLMService


class TestContentGenerator:
    """Test cases for ContentGenerator class."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        mock_service = Mock(spec=LLMService)
        return mock_service
    
    @pytest.fixture
    def mock_validator(self):
        """Create mock data validator."""
        mock_validator = Mock(spec=DataValidator)
        # Default to valid input
        mock_validator.validate_product_input.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[]
        )
        mock_validator.sanitize_text_input.side_effect = lambda x: x
        mock_validator.validate_csv_format.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[]
        )
        return mock_validator
    
    @pytest.fixture
    def content_generator(self, mock_llm_service, mock_validator):
        """Create ContentGenerator instance with mocked dependencies."""
        return ContentGenerator(mock_llm_service, mock_validator)
    
    @pytest.fixture
    def sample_product_input(self):
        """Create sample product input."""
        return ProductInput(
            name="Wireless Bluetooth Headphones",
            additional_attributes={
                "brand": "TechCorp",
                "price": "$99.99"
            }
        )
    
    @pytest.fixture
    def sample_ai_response(self):
        """Create sample AI response in JSON format."""
        return json.dumps({
            "title": "Premium Wireless Bluetooth Headphones - Crystal Clear Sound",
            "description": "Experience exceptional audio quality with these premium wireless Bluetooth headphones featuring advanced noise cancellation technology and comfortable over-ear design. With up to thirty hours of battery life these headphones are perfect for music lovers professionals and anyone who demands superior sound quality throughout their day. The ergonomic design ensures all-day comfort while the premium materials provide exceptional durability for long-term use. Connect seamlessly to any Bluetooth device and enjoy crystal clear calls with the built-in high-quality microphone system. Whether you're commuting working or relaxing at home these headphones deliver an immersive audio experience that brings your music to life with incredible detail and clarity.",
            "hashtags": ["#headphones", "#bluetooth", "#wireless", "#audio", "#music"]
        })
    
    def test_init(self, mock_llm_service, mock_validator):
        """Test ContentGenerator initialization."""
        generator = ContentGenerator(mock_llm_service, mock_validator)
        
        assert generator.llm_service == mock_llm_service
        assert generator.validator == mock_validator
        assert hasattr(generator, 'logger')
    
    def test_tone_profiles_available(self, content_generator):
        """Test that tone profiles are properly defined."""
        assert hasattr(content_generator, 'TONE_PROFILES')
        assert 'professional' in content_generator.TONE_PROFILES
        assert 'casual' in content_generator.TONE_PROFILES
        assert 'luxury' in content_generator.TONE_PROFILES
        
        # Check profile structure
        for tone, profile in content_generator.TONE_PROFILES.items():
            assert 'description' in profile
            assert 'keywords' in profile
            assert 'style' in profile
    
    def test_get_available_tones(self, content_generator):
        """Test getting available tone options."""
        tones = content_generator.get_available_tones()
        
        assert isinstance(tones, dict)
        assert 'professional' in tones
        assert 'casual' in tones
        assert len(tones) > 0
        
        # Check that descriptions are strings
        for tone, description in tones.items():
            assert isinstance(description, str)
            assert len(description) > 0
    
    def test_generate_single_product_content_success(
        self, content_generator, mock_llm_service, mock_validator, 
        sample_product_input, sample_ai_response
    ):
        """Test successful single product content generation."""
        # Setup mocks
        mock_llm_service.generate_content.return_value = sample_ai_response
        
        # Generate content
        result = content_generator.generate_single_product_content(
            sample_product_input, 'professional'
        )
        
        # Verify result
        assert isinstance(result, ProductContent)
        assert len(result.title) <= 60
        assert len(result.title) > 0
        assert len(result.description.split()) >= 100
        assert len(result.description.split()) <= 300
        assert len(result.hashtags) == 5
        assert all(hashtag.startswith('#') for hashtag in result.hashtags)
        
        # Verify mocks were called
        mock_validator.validate_product_input.assert_called_once_with(sample_product_input)
        mock_validator.sanitize_text_input.assert_called()
        mock_llm_service.generate_content.assert_called_once()
    
    def test_generate_single_product_content_invalid_input(
        self, content_generator, mock_validator, sample_product_input
    ):
        """Test content generation with invalid input."""
        # Setup mock to return invalid input
        mock_validator.validate_product_input.return_value = ValidationResult(
            is_valid=False, 
            errors=["Product name is required"], 
            warnings=[]
        )
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid product input"):
            content_generator.generate_single_product_content(
                sample_product_input, 'professional'
            )
    
    def test_generate_single_product_content_llm_failure(
        self, content_generator, mock_llm_service, sample_product_input
    ):
        """Test content generation when LLM service fails."""
        # Setup mock to raise exception
        mock_llm_service.generate_content.side_effect = Exception("API Error")
        
        # Should raise exception
        with pytest.raises(Exception, match="API Error"):
            content_generator.generate_single_product_content(
                sample_product_input, 'professional'
            )
    
    def test_extract_product_info_with_name(self, content_generator):
        """Test product info extraction with product name."""
        product_input = ProductInput(
            name="Test Product",
            additional_attributes={"brand": "TestBrand", "price": "$10"}
        )
        
        info = content_generator._extract_product_info(product_input)
        
        assert "Product Name: Test Product" in info
        assert "brand: TestBrand" in info
        assert "price: $10" in info
    
    def test_extract_product_info_with_image(self, content_generator):
        """Test product info extraction with image data."""
        product_input = ProductInput(
            name="Test Product",
            image_data=b"fake_image_data"
        )
        
        info = content_generator._extract_product_info(product_input)
        
        assert "Product Name: Test Product" in info
        assert "Image: Product image provided" in info
    
    def test_extract_product_info_empty(self, content_generator):
        """Test product info extraction with empty input."""
        product_input = ProductInput()
        
        info = content_generator._extract_product_info(product_input)
        
        assert "Product information not provided" in info
    
    def test_create_prompt_professional_tone(self, content_generator):
        """Test prompt creation with professional tone."""
        product_info = "Product Name: Test Product"
        
        prompt = content_generator._create_prompt(product_info, 'professional')
        
        assert "Test Product" in prompt
        assert "Professional" in prompt
        assert "JSON" in prompt
        assert "title" in prompt
        assert "description" in prompt
        assert "hashtags" in prompt
        assert "60 characters" in prompt
        assert "100-300 words" in prompt
    
    def test_create_prompt_luxury_tone(self, content_generator):
        """Test prompt creation with luxury tone."""
        product_info = "Product Name: Luxury Watch"
        
        prompt = content_generator._create_prompt(product_info, 'luxury')
        
        assert "Luxury" in prompt
        assert "sophisticated" in prompt or "exclusive" in prompt
    
    def test_parse_ai_response_valid_json(self, content_generator, sample_ai_response):
        """Test parsing valid JSON AI response."""
        result = content_generator._parse_ai_response(sample_ai_response)
        
        assert isinstance(result, ProductContent)
        assert result.title == "Premium Wireless Bluetooth Headphones - Crystal Clear Sound"
        assert len(result.description) > 100
        assert len(result.hashtags) == 5
        assert all(hashtag.startswith('#') for hashtag in result.hashtags)
    
    def test_parse_ai_response_with_markdown(self, content_generator):
        """Test parsing AI response with markdown formatting."""
        markdown_response = f"""```json
{json.dumps({
    "title": "Test Product Title",
    "description": "This is a test description with enough words to meet the minimum requirement. It contains multiple sentences to ensure proper length validation. The description provides detailed information about the product features and benefits for potential customers.",
    "hashtags": ["#test", "#product", "#example", "#demo", "#sample"]
})}
```"""
        
        result = content_generator._parse_ai_response(markdown_response)
        
        assert isinstance(result, ProductContent)
        assert result.title == "Test Product Title"
        assert len(result.hashtags) == 5
    
    def test_parse_ai_response_invalid_json(self, content_generator):
        """Test parsing invalid JSON response with regex fallback."""
        invalid_response = """
        Title: Test Product Title
        Description: This is a test description with enough words to meet the minimum requirement for content generation.
        Hashtags: #test #product #example #demo #sample
        """
        
        result = content_generator._parse_ai_response(invalid_response)
        
        assert isinstance(result, ProductContent)
        assert result.title == "Test Product Title"
        assert len(result.hashtags) >= 1
    
    def test_parse_ai_response_completely_invalid(self, content_generator):
        """Test parsing completely invalid response."""
        invalid_response = "This is not a valid response at all"
        
        with pytest.raises(ValueError, match="Could not parse AI response"):
            content_generator._parse_ai_response(invalid_response)
    
    def test_fix_content_issues_long_title(self, content_generator):
        """Test fixing content with title too long."""
        content = ProductContent(
            title="This is a very long title that exceeds the sixty character limit and needs to be truncated",
            description=" ".join(["word"] * 150),  # 150 words
            hashtags=["#test", "#product", "#example", "#demo", "#sample"]
        )
        
        fixed_content = content_generator._fix_content_issues(content)
        
        assert len(fixed_content.title) <= 60
        assert fixed_content.title.endswith("...")
    
    def test_fix_content_issues_short_description(self, content_generator):
        """Test fixing content with description too short."""
        content = ProductContent(
            title="Test Title",
            description="Short description",  # Less than 100 words
            hashtags=["#test", "#product", "#example", "#demo", "#sample"]
        )
        
        fixed_content = content_generator._fix_content_issues(content)
        
        assert len(fixed_content.description.split()) >= 100
    
    def test_fix_content_issues_wrong_hashtag_count(self, content_generator):
        """Test fixing content with wrong number of hashtags."""
        content = ProductContent(
            title="Test Title",
            description=" ".join(["word"] * 150),
            hashtags=["#test", "#product"]  # Only 2 hashtags
        )
        
        fixed_content = content_generator._fix_content_issues(content)
        
        assert len(fixed_content.hashtags) == 5
        assert all(hashtag.startswith('#') for hashtag in fixed_content.hashtags)
    
    def test_create_product_input_from_row(self, content_generator):
        """Test creating ProductInput from DataFrame row."""
        row = pd.Series({
            'product_name': 'Test Product',
            'brand': 'TestBrand',
            'price': '$99.99',
            'category': 'Electronics'
        })
        
        product_input = content_generator._create_product_input_from_row(row)
        
        assert product_input.name == 'Test Product'
        assert product_input.image_data is None
        assert product_input.additional_attributes['brand'] == 'TestBrand'
        assert product_input.additional_attributes['price'] == '$99.99'
        assert product_input.additional_attributes['category'] == 'Electronics'
    
    def test_create_product_input_from_row_missing_name(self, content_generator):
        """Test creating ProductInput from row without product name."""
        row = pd.Series({
            'brand': 'TestBrand',
            'price': '$99.99'
        })
        
        product_input = content_generator._create_product_input_from_row(row)
        
        assert product_input.name is None
        assert len(product_input.additional_attributes) == 2
    
    def test_generate_bulk_content_success(
        self, content_generator, mock_llm_service, mock_validator, sample_ai_response
    ):
        """Test successful bulk content generation."""
        # Setup test data
        test_df = pd.DataFrame({
            'product_name': ['Product 1', 'Product 2'],
            'brand': ['Brand A', 'Brand B']
        })
        
        # Setup mocks
        mock_llm_service.generate_content.return_value = sample_ai_response
        
        # Mock progress callback
        progress_callback = Mock()
        
        # Generate bulk content
        result_df = content_generator.generate_bulk_content(
            test_df, 'professional', progress_callback
        )
        
        # Verify result structure
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 2
        assert 'generated_title' in result_df.columns
        assert 'generated_description' in result_df.columns
        assert 'generated_hashtags' in result_df.columns
        assert 'processing_status' in result_df.columns
        assert 'error_message' in result_df.columns
        
        # Verify content was generated
        assert all(result_df['processing_status'] == 'success')
        assert all(result_df['generated_title'] != '')
        assert all(result_df['generated_description'] != '')
        assert all(result_df['generated_hashtags'] != '')
        
        # Verify progress callback was called
        assert progress_callback.call_count == 2
    
    def test_generate_bulk_content_invalid_csv(
        self, content_generator, mock_validator
    ):
        """Test bulk content generation with invalid CSV."""
        test_df = pd.DataFrame({'invalid_column': ['data']})
        
        # Setup mock to return invalid CSV
        mock_validator.validate_csv_format.return_value = ValidationResult(
            is_valid=False,
            errors=["Missing required columns: product_name"],
            warnings=[]
        )
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid CSV format"):
            content_generator.generate_bulk_content(test_df, 'professional')
    
    def test_generate_bulk_content_with_errors(
        self, content_generator, mock_llm_service, mock_validator
    ):
        """Test bulk content generation with some rows failing."""
        # Setup test data
        test_df = pd.DataFrame({
            'product_name': ['Product 1', 'Product 2']
        })
        
        # Setup mock to fail on second call
        mock_llm_service.generate_content.side_effect = [
            json.dumps({
                "title": "Product 1 Title",
                "description": " ".join(["word"] * 150),
                "hashtags": ["#test1", "#product1", "#example1", "#demo1", "#sample1"]
            }),
            Exception("API Error")
        ]
        
        # Generate bulk content
        result_df = content_generator.generate_bulk_content(test_df, 'professional')
        
        # Verify mixed results
        assert result_df.iloc[0]['processing_status'] == 'success'
        assert result_df.iloc[1]['processing_status'] == 'error'
        assert 'API Error' in result_df.iloc[1]['error_message']