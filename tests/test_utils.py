"""
Unit tests for the utils module including data models and validation.
"""

import pytest
import pandas as pd
from io import BytesIO
from utils import (
    ProductInput, ProductContent, ValidationResult, ProcessingProgress,
    DataValidator
)


class TestProductInput:
    """Test cases for ProductInput data model."""
    
    def test_valid_product_input_with_name(self):
        """Test valid product input with name only."""
        product = ProductInput(name="Test Product")
        result = product.validate()
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_valid_product_input_with_image(self):
        """Test valid product input with image data only."""
        product = ProductInput(image_data=b"fake_image_data")
        result = product.validate()
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_valid_product_input_with_both(self):
        """Test valid product input with both name and image."""
        product = ProductInput(
            name="Test Product",
            image_data=b"fake_image_data",
            additional_attributes={"category": "electronics"}
        )
        result = product.validate()
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_invalid_product_input_empty(self):
        """Test invalid product input with no data."""
        product = ProductInput()
        result = product.validate()
        assert not result.is_valid
        assert "Either product name or image data must be provided" in result.errors
    
    def test_invalid_product_name_empty_string(self):
        """Test invalid product input with empty name."""
        product = ProductInput(name="   ")
        result = product.validate()
        assert not result.is_valid
        assert "Product name cannot be empty" in result.errors
    
    def test_invalid_product_name_wrong_type(self):
        """Test invalid product input with wrong name type."""
        product = ProductInput(name=123)
        result = product.validate()
        assert not result.is_valid
        assert "Product name must be a string" in result.errors
    
    def test_invalid_image_data_empty(self):
        """Test invalid product input with empty image data."""
        product = ProductInput(image_data=b"")
        result = product.validate()
        assert not result.is_valid
        assert "Image data cannot be empty" in result.errors
    
    def test_invalid_image_data_wrong_type(self):
        """Test invalid product input with wrong image data type."""
        product = ProductInput(image_data="not_bytes")
        result = product.validate()
        assert not result.is_valid
        assert "Image data must be bytes" in result.errors
    
    def test_warning_long_product_name(self):
        """Test warning for very long product name."""
        long_name = "x" * 250
        product = ProductInput(name=long_name)
        result = product.validate()
        assert result.is_valid
        assert "Product name is very long" in result.warnings[0]
    
    def test_invalid_additional_attributes(self):
        """Test invalid additional attributes."""
        product = ProductInput(
            name="Test",
            additional_attributes={"key": 123}  # Non-string value
        )
        result = product.validate()
        assert not result.is_valid
        assert "Additional attribute 'key' must have string key and value" in result.errors


class TestProductContent:
    """Test cases for ProductContent data model."""
    
    def test_valid_product_content(self):
        """Test valid product content."""
        content = ProductContent(
            title="Great Product Title",
            description=" ".join(["word"] * 150),  # 150 words
            hashtags=["#product", "#great", "#sale", "#new", "#trending"]
        )
        result = content.validate()
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_invalid_title_too_long(self):
        """Test invalid title that's too long."""
        content = ProductContent(
            title="x" * 70,  # Too long
            description=" ".join(["word"] * 150),
            hashtags=["#product", "#great", "#sale", "#new", "#trending"]
        )
        result = content.validate()
        assert not result.is_valid
        assert "Title must be ≤60 characters" in result.errors[0]
    
    def test_invalid_title_empty(self):
        """Test invalid empty title."""
        content = ProductContent(
            title="",
            description=" ".join(["word"] * 150),
            hashtags=["#product", "#great", "#sale", "#new", "#trending"]
        )
        result = content.validate()
        assert not result.is_valid
        assert "Title cannot be empty" in result.errors
    
    def test_invalid_title_wrong_type(self):
        """Test invalid title with wrong type."""
        content = ProductContent(
            title=123,
            description=" ".join(["word"] * 150),
            hashtags=["#product", "#great", "#sale", "#new", "#trending"]
        )
        result = content.validate()
        assert not result.is_valid
        assert "Title must be a string" in result.errors
    
    def test_invalid_description_too_short(self):
        """Test invalid description that's too short."""
        content = ProductContent(
            title="Good Title",
            description=" ".join(["word"] * 50),  # Too short
            hashtags=["#product", "#great", "#sale", "#new", "#trending"]
        )
        result = content.validate()
        assert not result.is_valid
        assert "Description must be at least 100 words" in result.errors[0]
    
    def test_invalid_description_too_long(self):
        """Test invalid description that's too long."""
        content = ProductContent(
            title="Good Title",
            description=" ".join(["word"] * 350),  # Too long
            hashtags=["#product", "#great", "#sale", "#new", "#trending"]
        )
        result = content.validate()
        assert not result.is_valid
        assert "Description must be at most 300 words" in result.errors[0]
    
    def test_invalid_description_empty(self):
        """Test invalid empty description."""
        content = ProductContent(
            title="Good Title",
            description="   ",
            hashtags=["#product", "#great", "#sale", "#new", "#trending"]
        )
        result = content.validate()
        assert not result.is_valid
        assert "Description cannot be empty" in result.errors
    
    def test_invalid_description_wrong_type(self):
        """Test invalid description with wrong type."""
        content = ProductContent(
            title="Good Title",
            description=123,
            hashtags=["#product", "#great", "#sale", "#new", "#trending"]
        )
        result = content.validate()
        assert not result.is_valid
        assert "Description must be a string" in result.errors
    
    def test_invalid_hashtags_wrong_count(self):
        """Test invalid hashtag count."""
        content = ProductContent(
            title="Good Title",
            description=" ".join(["word"] * 150),
            hashtags=["#product", "#great", "#sale"]  # Only 3 hashtags
        )
        result = content.validate()
        assert not result.is_valid
        assert "Must have exactly 5 hashtags" in result.errors[0]
    
    def test_invalid_hashtags_wrong_type(self):
        """Test invalid hashtags with wrong type."""
        content = ProductContent(
            title="Good Title",
            description=" ".join(["word"] * 150),
            hashtags="not_a_list"
        )
        result = content.validate()
        assert not result.is_valid
        assert "Hashtags must be a list" in result.errors
    
    def test_invalid_hashtag_no_hash(self):
        """Test invalid hashtag without # symbol."""
        content = ProductContent(
            title="Good Title",
            description=" ".join(["word"] * 150),
            hashtags=["#product", "great", "#sale", "#new", "#trending"]  # Missing #
        )
        result = content.validate()
        assert not result.is_valid
        assert "Hashtag 2 must start with '#'" in result.errors
    
    def test_invalid_hashtag_too_short(self):
        """Test invalid hashtag that's too short."""
        content = ProductContent(
            title="Good Title",
            description=" ".join(["word"] * 150),
            hashtags=["#product", "#", "#sale", "#new", "#trending"]  # Too short
        )
        result = content.validate()
        assert not result.is_valid
        assert "Hashtag 2 is too short" in result.errors
    
    def test_invalid_hashtag_invalid_characters(self):
        """Test invalid hashtag with invalid characters."""
        content = ProductContent(
            title="Good Title",
            description=" ".join(["word"] * 150),
            hashtags=["#product", "#great-sale", "#sale", "#new", "#trending"]  # Dash not allowed
        )
        result = content.validate()
        assert not result.is_valid
        assert "Hashtag 2 contains invalid characters (only letters, numbers, and underscores allowed)" in result.errors
    
    def test_warning_long_hashtag(self):
        """Test warning for very long hashtag."""
        content = ProductContent(
            title="Good Title",
            description=" ".join(["word"] * 150),
            hashtags=["#product", "#" + "x" * 35, "#sale", "#new", "#trending"]  # Very long
        )
        result = content.validate()
        assert result.is_valid
        assert "Hashtag 2 is very long" in result.warnings[0]
    
    def test_word_count_method(self):
        """Test word count method."""
        content = ProductContent(
            title="Title",
            description="This is a test description with exactly seven words",
            hashtags=["#test", "#desc", "#seven", "#words", "#count"]
        )
        assert content.word_count() == 9


class TestDataValidator:
    """Test cases for DataValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
    
    def test_validate_product_input_valid(self):
        """Test validation of valid product input."""
        product = ProductInput(name="Test Product")
        result = self.validator.validate_product_input(product)
        assert result.is_valid
    
    def test_validate_product_input_invalid_type(self):
        """Test validation of invalid product input type."""
        result = self.validator.validate_product_input("not_a_product")
        assert not result.is_valid
        assert "Input must be a ProductInput instance" in result.errors
    
    def test_sanitize_text_input_basic(self):
        """Test basic text sanitization."""
        text = "Normal text input"
        result = self.validator.sanitize_text_input(text)
        assert result == "Normal text input"
    
    def test_sanitize_text_input_script_tags(self):
        """Test sanitization removes script tags."""
        text = "Hello <script>alert('xss')</script> world"
        result = self.validator.sanitize_text_input(text)
        assert result == "Hello world"
    
    def test_sanitize_text_input_html_tags(self):
        """Test sanitization removes HTML tags."""
        text = "Hello <b>bold</b> and <i>italic</i> text"
        result = self.validator.sanitize_text_input(text)
        assert result == "Hello bold and italic text"
    
    def test_sanitize_text_input_javascript_urls(self):
        """Test sanitization removes javascript URLs."""
        text = "Click javascript: alert('xss') here"
        result = self.validator.sanitize_text_input(text)
        assert result == "Click alert('xss') here"
    
    def test_sanitize_text_input_event_handlers(self):
        """Test sanitization removes event handlers."""
        text = "Text with onclick=alert('xss') handler"
        result = self.validator.sanitize_text_input(text)
        assert result == "Text with handler"
    
    def test_sanitize_text_input_whitespace(self):
        """Test sanitization normalizes whitespace."""
        text = "Text   with    lots\n\nof\t\twhitespace"
        result = self.validator.sanitize_text_input(text)
        assert result == "Text with lots of whitespace"
    
    def test_sanitize_text_input_wrong_type(self):
        """Test sanitization with wrong input type."""
        result = self.validator.sanitize_text_input(123)
        assert result == ""
    
    def test_validate_file_size_valid(self):
        """Test validation of valid file size."""
        small_file = BytesIO(b"x" * 1000)  # 1KB
        assert self.validator.validate_file_size(small_file)
    
    def test_validate_file_size_too_large(self):
        """Test validation of file that's too large."""
        # Create a file larger than 50MB
        large_file = BytesIO(b"x" * (51 * 1024 * 1024))
        assert not self.validator.validate_file_size(large_file)
    
    def test_validate_file_size_wrong_type(self):
        """Test validation with wrong file type."""
        assert not self.validator.validate_file_size("not_a_file")
    
    def test_validate_csv_columns_valid(self):
        """Test CSV column validation with valid columns."""
        df = pd.DataFrame({"product_name": ["Product 1", "Product 2"]})
        missing = self.validator.validate_csv_columns(df)
        assert len(missing) == 0
    
    def test_validate_csv_columns_missing(self):
        """Test CSV column validation with missing columns."""
        df = pd.DataFrame({"other_column": ["Value 1", "Value 2"]})
        missing = self.validator.validate_csv_columns(df)
        assert "product_name" in missing
    
    def test_validate_csv_columns_wrong_type(self):
        """Test CSV column validation with wrong input type."""
        missing = self.validator.validate_csv_columns("not_a_dataframe")
        assert missing == self.validator.REQUIRED_CSV_COLUMNS
    
    def test_validate_csv_format_valid(self):
        """Test comprehensive CSV format validation with valid data."""
        df = pd.DataFrame({
            "product_name": ["Product 1", "Product 2"],
            "category": ["Electronics", "Clothing"]
        })
        result = self.validator.validate_csv_format(df)
        assert result.is_valid
    
    def test_validate_csv_format_missing_columns(self):
        """Test CSV format validation with missing required columns."""
        df = pd.DataFrame({"other_column": ["Value 1", "Value 2"]})
        result = self.validator.validate_csv_format(df)
        assert not result.is_valid
        assert "Missing required columns: product_name" in result.errors
    
    def test_validate_csv_format_empty(self):
        """Test CSV format validation with empty DataFrame."""
        df = pd.DataFrame()
        result = self.validator.validate_csv_format(df)
        assert not result.is_valid
        assert "CSV file is empty" in result.errors
    
    def test_validate_csv_format_null_names(self):
        """Test CSV format validation with null product names."""
        df = pd.DataFrame({
            "product_name": ["Product 1", None, "Product 3"]
        })
        result = self.validator.validate_csv_format(df)
        assert result.is_valid  # Should be valid but with warnings
        assert "1 rows have missing product names" in result.warnings[0]
    
    def test_validate_csv_format_long_names(self):
        """Test CSV format validation with very long product names."""
        df = pd.DataFrame({
            "product_name": ["Product 1", "x" * 250, "Product 3"]
        })
        result = self.validator.validate_csv_format(df)
        assert result.is_valid  # Should be valid but with warnings
        assert "1 rows have very long product names" in result.warnings[0]
    
    def test_validate_csv_format_large_file(self):
        """Test CSV format validation with large file."""
        # Create a large DataFrame
        df = pd.DataFrame({
            "product_name": [f"Product {i}" for i in range(15000)]
        })
        result = self.validator.validate_csv_format(df)
        assert result.is_valid  # Should be valid but with warnings
        assert "Large file with 15000 rows" in result.warnings[0]
    
    def test_validate_csv_format_wrong_type(self):
        """Test CSV format validation with wrong input type."""
        result = self.validator.validate_csv_format("not_a_dataframe")
        assert not result.is_valid
        assert "Input must be a pandas DataFrame" in result.errors
    
    def test_validate_file_extension_valid(self):
        """Test file extension validation with valid extensions."""
        assert self.validator.validate_file_extension("data.csv")
        assert self.validator.validate_file_extension("data.tsv")
        assert self.validator.validate_file_extension("DATA.CSV")  # Case insensitive
    
    def test_validate_file_extension_invalid(self):
        """Test file extension validation with invalid extensions."""
        assert not self.validator.validate_file_extension("data.txt")
        assert not self.validator.validate_file_extension("data.xlsx")
        assert not self.validator.validate_file_extension("data")
    
    def test_validate_file_extension_wrong_type(self):
        """Test file extension validation with wrong input type."""
        assert not self.validator.validate_file_extension(123)
        assert not self.validator.validate_file_extension(None)


class TestValidationResult:
    """Test cases for ValidationResult data model."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult(
            is_valid=True,
            errors=["error1"],
            warnings=["warning1"]
        )
        assert result.is_valid
        assert result.errors == ["error1"]
        assert result.warnings == ["warning1"]
    
    def test_validation_result_default_warnings(self):
        """Test ValidationResult with default warnings."""
        result = ValidationResult(is_valid=False, errors=["error1"])
        assert not result.is_valid
        assert result.errors == ["error1"]
        assert result.warnings == []


class TestProcessingProgress:
    """Test cases for ProcessingProgress data model."""
    
    def test_processing_progress_creation(self):
        """Test ProcessingProgress creation."""
        progress = ProcessingProgress(
            current=5,
            total=10,
            status="Processing",
            errors=["error1"]
        )
        assert progress.current == 5
        assert progress.total == 10
        assert progress.status == "Processing"
        assert progress.errors == ["error1"]
    
    def test_processing_progress_default_errors(self):
        """Test ProcessingProgress with default errors."""
        progress = ProcessingProgress(current=3, total=10, status="Running")
        assert progress.current == 3
        assert progress.total == 10
        assert progress.status == "Running"
        assert progress.errors == []


class TestConfigurationManager:
    """Test cases for ConfigurationManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Import here to avoid circular imports during module loading
        from utils import ConfigurationManager
        
        # Store original environment variables
        import os
        self.original_env = os.environ.copy()
        
        # Clear relevant environment variables for clean testing
        env_vars_to_clear = [
            'OPENAI_API_KEY', 'APP_ENV', 'DEBUG', 'MAX_FILE_SIZE_MB',
            'CSV_CHUNK_SIZE', 'MAX_RETRIES', 'RETRY_DELAY_BASE', 'RATE_LIMIT_DELAY'
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]
    
    def teardown_method(self):
        """Clean up after tests."""
        # Restore original environment variables
        import os
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_configuration_manager_initialization(self):
        """Test ConfigurationManager initialization with default values."""
        from utils import ConfigurationManager
        
        config_manager = ConfigurationManager()
        
        # Check that default values are loaded
        assert config_manager.get_config_value('APP_ENV') == 'development'
        assert config_manager.get_config_value('DEBUG') == 'true'
        assert config_manager.get_config_value('MAX_FILE_SIZE_MB') == '50'
        assert config_manager.get_config_value('CSV_CHUNK_SIZE') == '100'
        assert config_manager.get_config_value('MAX_RETRIES') == '3'
        assert config_manager.get_config_value('RETRY_DELAY_BASE') == '1.0'
        assert config_manager.get_config_value('RATE_LIMIT_DELAY') == '60'
    
    def test_configuration_manager_with_environment_variables(self):
        """Test ConfigurationManager with custom environment variables."""
        import os
        from utils import ConfigurationManager
        
        # Set custom environment variables
        os.environ['OPENAI_API_KEY'] = 'sk-test-key-12345678901234567890123456789012345'
        os.environ['APP_ENV'] = 'production'
        os.environ['DEBUG'] = 'false'
        os.environ['MAX_FILE_SIZE_MB'] = '100'
        
        config_manager = ConfigurationManager()
        
        # Check that environment variables are loaded
        assert config_manager.get_config_value('OPENAI_API_KEY') == 'sk-test-key-12345678901234567890123456789012345'
        assert config_manager.get_config_value('APP_ENV') == 'production'
        assert config_manager.get_config_value('DEBUG') == 'false'
        assert config_manager.get_config_value('MAX_FILE_SIZE_MB') == '100'
    
    def test_validate_api_key_missing(self):
        """Test API key validation with missing key."""
        from utils import ConfigurationManager
        
        config_manager = ConfigurationManager()
        assert not config_manager.validate_api_key()
    
    def test_validate_api_key_placeholder(self):
        """Test API key validation with placeholder value."""
        import os
        from utils import ConfigurationManager
        
        os.environ['OPENAI_API_KEY'] = 'your_openai_api_key_here'
        config_manager = ConfigurationManager()
        assert not config_manager.validate_api_key()
    
    def test_validate_api_key_invalid_format(self):
        """Test API key validation with invalid format."""
        import os
        from utils import ConfigurationManager
        
        # Test key that doesn't start with 'sk-'
        os.environ['OPENAI_API_KEY'] = 'invalid-key-format'
        config_manager = ConfigurationManager()
        assert not config_manager.validate_api_key()
        
        # Test key that's too short
        os.environ['OPENAI_API_KEY'] = 'sk-short'
        config_manager = ConfigurationManager()
        assert not config_manager.validate_api_key()
    
    def test_validate_api_key_valid(self):
        """Test API key validation with valid key."""
        import os
        from utils import ConfigurationManager
        
        os.environ['OPENAI_API_KEY'] = 'sk-test-key-12345678901234567890123456789012345'
        config_manager = ConfigurationManager()
        assert config_manager.validate_api_key()
    
    def test_get_openai_client_invalid_key(self):
        """Test OpenAI client creation with invalid key."""
        from utils import ConfigurationManager
        
        config_manager = ConfigurationManager()
        
        with pytest.raises(ValueError, match="Invalid or missing OpenAI API key"):
            config_manager.get_openai_client()
    
    def test_get_openai_client_valid_key(self):
        """Test OpenAI client creation with valid key."""
        import os
        from utils import ConfigurationManager
        
        os.environ['OPENAI_API_KEY'] = 'sk-test-key-12345678901234567890123456789012345'
        config_manager = ConfigurationManager()
        
        # This should not raise an exception
        client = config_manager.get_openai_client()
        assert client is not None
    
    def test_get_config_value(self):
        """Test getting configuration values."""
        import os
        from utils import ConfigurationManager
        
        os.environ['TEST_KEY'] = 'test_value'
        config_manager = ConfigurationManager()
        
        # Test existing key
        assert config_manager.get_config_value('APP_ENV') == 'development'
        
        # Test non-existing key with default
        assert config_manager.get_config_value('NON_EXISTING', 'default') == 'default'
        
        # Test non-existing key without default
        assert config_manager.get_config_value('NON_EXISTING') is None
    
    def test_get_int_config(self):
        """Test getting integer configuration values."""
        import os
        from utils import ConfigurationManager
        
        os.environ['INT_VALUE'] = '42'
        os.environ['INVALID_INT'] = 'not_a_number'
        config_manager = ConfigurationManager()
        
        # Test valid integer
        assert config_manager.get_int_config('MAX_FILE_SIZE_MB') == 50
        
        # Test invalid integer with default
        assert config_manager.get_int_config('INVALID_INT', 10) == 10
        
        # Test non-existing key with default
        assert config_manager.get_int_config('NON_EXISTING', 5) == 5
    
    def test_get_float_config(self):
        """Test getting float configuration values."""
        import os
        from utils import ConfigurationManager
        
        os.environ['FLOAT_VALUE'] = '3.14'
        os.environ['INVALID_FLOAT'] = 'not_a_number'
        config_manager = ConfigurationManager()
        
        # Test valid float
        assert config_manager.get_float_config('RETRY_DELAY_BASE') == 1.0
        
        # Test invalid float with default
        assert config_manager.get_float_config('INVALID_FLOAT', 2.5) == 2.5
        
        # Test non-existing key with default
        assert config_manager.get_float_config('NON_EXISTING', 1.5) == 1.5
    
    def test_get_bool_config(self):
        """Test getting boolean configuration values."""
        import os
        from utils import ConfigurationManager
        
        os.environ['BOOL_TRUE'] = 'true'
        os.environ['BOOL_FALSE'] = 'false'
        os.environ['BOOL_YES'] = 'yes'
        os.environ['BOOL_NO'] = 'no'
        os.environ['BOOL_1'] = '1'
        os.environ['BOOL_0'] = '0'
        config_manager = ConfigurationManager()
        
        # Test various true values
        assert config_manager.get_bool_config('BOOL_TRUE') is True
        assert config_manager.get_bool_config('BOOL_YES') is True
        assert config_manager.get_bool_config('BOOL_1') is True
        
        # Test various false values
        assert config_manager.get_bool_config('BOOL_FALSE') is False
        assert config_manager.get_bool_config('BOOL_NO') is False
        assert config_manager.get_bool_config('BOOL_0') is False
        
        # Test default value
        assert config_manager.get_bool_config('NON_EXISTING', True) is True
    
    def test_environment_detection_methods(self):
        """Test environment detection methods."""
        import os
        from utils import ConfigurationManager
        
        # Test development environment (default)
        config_manager = ConfigurationManager()
        assert config_manager.is_development() is True
        assert config_manager.is_production() is False
        assert config_manager.is_test() is False
        
        # Test production environment
        os.environ['APP_ENV'] = 'production'
        config_manager = ConfigurationManager()
        assert config_manager.is_development() is False
        assert config_manager.is_production() is True
        assert config_manager.is_test() is False
        
        # Test test environment
        os.environ['APP_ENV'] = 'test'
        config_manager = ConfigurationManager()
        assert config_manager.is_development() is False
        assert config_manager.is_production() is False
        assert config_manager.is_test() is True
    
    def test_get_setup_instructions_missing_api_key(self):
        """Test setup instructions when API key is missing."""
        from utils import ConfigurationManager
        
        config_manager = ConfigurationManager()
        instructions = config_manager.get_setup_instructions()
        
        assert "OpenAI API Key is missing or invalid" in instructions
        assert "https://platform.openai.com/" in instructions
        assert "OPENAI_API_KEY=sk-your-actual-key-here" in instructions
    
    def test_get_setup_instructions_complete_config(self):
        """Test setup instructions when configuration is complete."""
        import os
        from utils import ConfigurationManager
        
        os.environ['OPENAI_API_KEY'] = 'sk-test-key-12345678901234567890123456789012345'
        config_manager = ConfigurationManager()
        instructions = config_manager.get_setup_instructions()
        
        assert "Configuration is complete!" in instructions
    
    def test_validate_configuration_valid(self):
        """Test configuration validation with valid settings."""
        import os
        from utils import ConfigurationManager
        
        os.environ['OPENAI_API_KEY'] = 'sk-test-key-12345678901234567890123456789012345'
        os.environ['MAX_FILE_SIZE_MB'] = '50'
        os.environ['CSV_CHUNK_SIZE'] = '100'
        os.environ['MAX_RETRIES'] = '3'
        os.environ['RETRY_DELAY_BASE'] = '1.0'
        
        config_manager = ConfigurationManager()
        result = config_manager.validate_configuration()
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_configuration_missing_api_key(self):
        """Test configuration validation with missing API key."""
        from utils import ConfigurationManager
        
        config_manager = ConfigurationManager()
        result = config_manager.validate_configuration()
        
        assert not result.is_valid
        assert "OpenAI API key is missing or invalid" in result.errors
    
    def test_validate_configuration_invalid_numeric_values(self):
        """Test configuration validation with invalid numeric values."""
        import os
        from utils import ConfigurationManager
        
        os.environ['OPENAI_API_KEY'] = 'sk-test-key-12345678901234567890123456789012345'
        os.environ['MAX_FILE_SIZE_MB'] = '-10'  # Negative value
        os.environ['CSV_CHUNK_SIZE'] = 'not_a_number'  # Invalid integer
        os.environ['MAX_RETRIES'] = '-1'  # Negative value
        os.environ['RETRY_DELAY_BASE'] = 'invalid'  # Invalid float
        
        config_manager = ConfigurationManager()
        result = config_manager.validate_configuration()
        
        assert not result.is_valid
        assert "MAX_FILE_SIZE_MB must be a positive integer" in result.errors
        assert "CSV_CHUNK_SIZE must be a valid integer" in result.errors
        assert "MAX_RETRIES must be non-negative" in result.errors
        assert "RETRY_DELAY_BASE must be a valid number" in result.errors
    
    def test_validate_configuration_warnings(self):
        """Test configuration validation with warning conditions."""
        import os
        from utils import ConfigurationManager
        
        os.environ['OPENAI_API_KEY'] = 'sk-test-key-12345678901234567890123456789012345'
        os.environ['MAX_FILE_SIZE_MB'] = '1000'  # Very large
        os.environ['CSV_CHUNK_SIZE'] = '50000'  # Very large
        os.environ['MAX_RETRIES'] = '20'  # Very high
        os.environ['APP_ENV'] = 'staging'  # Non-standard environment
        
        config_manager = ConfigurationManager()
        result = config_manager.validate_configuration()
        
        assert result.is_valid  # Should be valid but with warnings
        assert "MAX_FILE_SIZE_MB is very large" in result.warnings[0]
        assert "CSV_CHUNK_SIZE is very large" in result.warnings[1]
        assert "MAX_RETRIES is very high" in result.warnings[2]
        assert "APP_ENV 'staging' is not a standard environment" in result.warnings[3]
    
    def test_get_safe_config_summary(self):
        """Test getting safe configuration summary with masked sensitive data."""
        import os
        from utils import ConfigurationManager
        
        os.environ['OPENAI_API_KEY'] = 'sk-test-key-12345678901234567890123456789012345'
        os.environ['APP_ENV'] = 'development'
        
        config_manager = ConfigurationManager()
        safe_config = config_manager.get_safe_config_summary()
        
        # Check that API key is masked
        assert safe_config['OPENAI_API_KEY'].startswith('sk-t')
        assert '*' in safe_config['OPENAI_API_KEY']
        
        # Check that non-sensitive values are not masked
        assert safe_config['APP_ENV'] == 'development'
        assert safe_config['MAX_FILE_SIZE_MB'] == '50'
    
    def test_get_safe_config_summary_short_key(self):
        """Test safe config summary with short sensitive value."""
        import os
        from utils import ConfigurationManager
        
        os.environ['OPENAI_API_KEY'] = 'sk'  # Very short key
        
        config_manager = ConfigurationManager()
        safe_config = config_manager.get_safe_config_summary()
        
        # Short keys should be completely masked
        assert safe_config['OPENAI_API_KEY'] == '***'
    
    def test_get_safe_config_summary_missing_values(self):
        """Test safe config summary with missing values."""
        from utils import ConfigurationManager
        
        config_manager = ConfigurationManager()
        safe_config = config_manager.get_safe_config_summary()
        
        # Missing API key should show "Not set"
        assert safe_config['OPENAI_API_KEY'] == "Not set"


class TestErrorHandler:
    """Test cases for ErrorHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from utils import ErrorHandler, ConfigurationManager
        import os
        
        # Store original environment variables
        self.original_env = os.environ.copy()
        
        # Set up test environment
        os.environ['OPENAI_API_KEY'] = 'sk-test-key-12345678901234567890123456789012345'
        os.environ['APP_ENV'] = 'test'
        os.environ['MAX_RETRIES'] = '2'
        os.environ['RETRY_DELAY_BASE'] = '0.1'  # Fast retries for testing
        
        self.config_manager = ConfigurationManager()
        self.error_handler = ErrorHandler(self.config_manager)
    
    def teardown_method(self):
        """Clean up after tests."""
        import os
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        from utils import ErrorHandler
        
        # Test with config manager
        error_handler = ErrorHandler(self.config_manager)
        assert error_handler.config_manager is not None
        assert error_handler.partial_results == {}
        
        # Test without config manager (should create default)
        error_handler = ErrorHandler()
        assert error_handler.config_manager is not None
    
    def test_retry_with_exponential_backoff_success_first_try(self):
        """Test retry logic when function succeeds on first try."""
        call_count = 0
        
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = self.error_handler.retry_with_exponential_backoff(successful_function)
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_with_exponential_backoff_success_after_retries(self):
        """Test retry logic when function succeeds after some failures."""
        call_count = 0
        
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"
        
        result = self.error_handler.retry_with_exponential_backoff(eventually_successful_function)
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_with_exponential_backoff_all_retries_fail(self):
        """Test retry logic when all retries are exhausted."""
        call_count = 0
        
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent network error")
        
        with pytest.raises(ConnectionError, match="Persistent network error"):
            self.error_handler.retry_with_exponential_backoff(always_failing_function)
        
        assert call_count == 3  # Initial attempt + 2 retries
    
    def test_retry_with_exponential_backoff_non_retryable_exception(self):
        """Test retry logic with non-retryable exception."""
        call_count = 0
        
        def function_with_non_retryable_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("This should not be retried")
        
        with pytest.raises(ValueError, match="This should not be retried"):
            self.error_handler.retry_with_exponential_backoff(
                function_with_non_retryable_error,
                retryable_exceptions=(ConnectionError, TimeoutError)
            )
        
        assert call_count == 1  # Should not retry
    
    def test_retry_with_exponential_backoff_custom_parameters(self):
        """Test retry logic with custom parameters."""
        call_count = 0
        
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network error")
        
        with pytest.raises(ConnectionError):
            self.error_handler.retry_with_exponential_backoff(
                failing_function,
                max_retries=1,
                base_delay=0.01
            )
        
        assert call_count == 2  # Initial attempt + 1 retry
    
    def test_handle_api_error_rate_limit(self):
        """Test API error handling for rate limit errors."""
        error = Exception("Rate limit exceeded")
        message = self.error_handler.handle_api_error(error, "test context")
        
        assert "rate limit exceeded" in message.lower()
        assert "wait a moment" in message.lower()
    
    def test_handle_api_error_authentication(self):
        """Test API error handling for authentication errors."""
        error = Exception("Invalid API key provided")
        message = self.error_handler.handle_api_error(error, "test context")
        
        assert "authentication failed" in message.lower()
        assert "api key" in message.lower()
    
    def test_handle_api_error_quota_exceeded(self):
        """Test API error handling for quota exceeded errors."""
        error = Exception("Insufficient quota remaining")
        message = self.error_handler.handle_api_error(error, "test context")
        
        assert "insufficient api quota" in message.lower()
        assert "billing" in message.lower()
    
    def test_handle_api_error_timeout(self):
        """Test API error handling for timeout errors."""
        error = TimeoutError("Request timed out")
        message = self.error_handler.handle_api_error(error, "test context")
        
        assert "timed out" in message.lower()
        assert "try again" in message.lower()
    
    def test_handle_api_error_connection(self):
        """Test API error handling for connection errors."""
        error = ConnectionError("Connection failed")
        message = self.error_handler.handle_api_error(error, "test context")
        
        assert "connection error" in message.lower()
        assert "internet connection" in message.lower()
    
    def test_handle_api_error_model_not_found(self):
        """Test API error handling for model not found errors."""
        error = Exception("Model gpt-4o not found")
        message = self.error_handler.handle_api_error(error, "test context")
        
        assert "model" in message.lower()
        assert "not available" in message.lower()
    
    def test_handle_api_error_generic(self):
        """Test API error handling for generic errors."""
        error = Exception("Unknown API error")
        message = self.error_handler.handle_api_error(error, "test context")
        
        assert "unexpected error" in message.lower()
        assert "Exception" in message  # Should include error type
    
    def test_handle_file_error_file_not_found(self):
        """Test file error handling for file not found."""
        error = FileNotFoundError("File not found")
        message = self.error_handler.handle_file_error(error, "test context")
        
        assert "file not found" in message.lower()
        assert "permission" in message.lower()
    
    def test_handle_file_error_permission_denied(self):
        """Test file error handling for permission errors."""
        error = PermissionError("Permission denied")
        message = self.error_handler.handle_file_error(error, "test context")
        
        assert "permission denied" in message.lower()
        assert "permissions" in message.lower()
    
    def test_handle_file_error_memory_error(self):
        """Test file error handling for memory errors."""
        error = MemoryError("Out of memory")
        message = self.error_handler.handle_file_error(error, "test context")
        
        assert "too large" in message.lower()
        assert "smaller file" in message.lower()
    
    def test_handle_file_error_csv_parse_error(self):
        """Test file error handling for CSV parsing errors."""
        error = Exception("CSV parse error: invalid format")
        message = self.error_handler.handle_file_error(error, "test context")
        
        assert "invalid csv format" in message.lower()
        assert "product_name" in message.lower()
    
    def test_handle_file_error_encoding_error(self):
        """Test file error handling for encoding errors."""
        error = Exception("UnicodeDecodeError: invalid encoding")
        message = self.error_handler.handle_file_error(error, "test context")
        
        assert "encoding error" in message.lower()
        assert "utf-8" in message.lower()
    
    def test_handle_file_error_size_limit(self):
        """Test file error handling for size limit errors."""
        error = Exception("File size exceeds limit")
        message = self.error_handler.handle_file_error(error, "test context")
        
        assert "size exceeds" in message.lower()
        assert "50mb" in message.lower()
    
    def test_handle_file_error_generic(self):
        """Test file error handling for generic errors."""
        error = Exception("Unknown file error")
        message = self.error_handler.handle_file_error(error, "test context")
        
        assert "file processing error" in message.lower()
        assert "Exception" in message
    
    def test_handle_validation_error_with_errors(self):
        """Test validation error handling with errors."""
        from utils import ValidationResult
        
        validation_result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        
        message = self.error_handler.handle_validation_error(validation_result, "test context")
        
        assert "Validation Errors" in message
        assert "Error 1" in message
        assert "Error 2" in message
        assert "Warnings" in message
        assert "Warning 1" in message
    
    def test_handle_validation_error_valid_result(self):
        """Test validation error handling with valid result."""
        from utils import ValidationResult
        
        validation_result = ValidationResult(is_valid=True, errors=[])
        message = self.error_handler.handle_validation_error(validation_result, "test context")
        
        assert message == ""
    
    def test_preserve_partial_results(self):
        """Test preserving partial results."""
        test_results = {"processed": 5, "total": 10}
        operation_id = "test_operation_123"
        
        self.error_handler.preserve_partial_results(operation_id, test_results)
        
        assert self.error_handler.has_partial_results(operation_id)
        retrieved_results = self.error_handler.get_partial_results(operation_id)
        assert retrieved_results == test_results
    
    def test_get_partial_results_not_found(self):
        """Test getting partial results when none exist."""
        result = self.error_handler.get_partial_results("nonexistent_operation")
        assert result is None
    
    def test_clear_partial_results(self):
        """Test clearing partial results."""
        operation_id = "test_operation_456"
        test_results = {"data": "test"}
        
        self.error_handler.preserve_partial_results(operation_id, test_results)
        assert self.error_handler.has_partial_results(operation_id)
        
        self.error_handler.clear_partial_results(operation_id)
        assert not self.error_handler.has_partial_results(operation_id)
    
    def test_get_recovery_options_with_partial_results(self):
        """Test getting recovery options when partial results exist."""
        operation_id = "test_operation_789"
        test_results = {"processed": 3, "total": 10}
        
        self.error_handler.preserve_partial_results(operation_id, test_results)
        options = self.error_handler.get_recovery_options(operation_id)
        
        assert options['can_recover'] is True
        assert options['resume_available'] is True
        assert "partial results" in options['message'].lower()
        assert 'timestamp' in options
    
    def test_get_recovery_options_without_partial_results(self):
        """Test getting recovery options when no partial results exist."""
        options = self.error_handler.get_recovery_options("nonexistent_operation")
        
        assert options['can_recover'] is False
        assert "no partial results" in options['message'].lower()
    
    def test_log_error_development_mode(self):
        """Test error logging in development mode."""
        import os
        from utils import ErrorHandler, ConfigurationManager
        
        # Set development mode
        os.environ['APP_ENV'] = 'development'
        config_manager = ConfigurationManager()
        error_handler = ErrorHandler(config_manager)
        
        # This should not raise an exception
        error = ValueError("Test error")
        error_handler.log_error(error, "test context")
        
        # Verify logger was set up (basic check)
        assert error_handler.logger is not None
    
    def test_log_error_production_mode(self):
        """Test error logging in production mode."""
        import os
        from utils import ErrorHandler, ConfigurationManager
        
        # Set production mode
        os.environ['APP_ENV'] = 'production'
        config_manager = ConfigurationManager()
        error_handler = ErrorHandler(config_manager)
        
        # This should not raise an exception
        error = ValueError("Test error")
        error_handler.log_error(error, "test context")
        
        # Verify logger was set up (basic check)
        assert error_handler.logger is not None
    
    def test_create_user_friendly_message_with_suggestions(self):
        """Test creating user-friendly messages with suggestions."""
        error = ConnectionError("Network connection failed")
        suggestions = ["Check your internet connection", "Try again later"]
        
        message = self.error_handler.create_user_friendly_message(
            error, "uploading file", suggestions
        )
        
        assert "connection error" in message.lower()
        assert "suggestions" in message.lower()
        assert "Check your internet connection" in message
        assert "Try again later" in message
        assert "contact support" in message.lower()
    
    def test_create_user_friendly_message_without_suggestions(self):
        """Test creating user-friendly messages without suggestions."""
        error = ValueError("Invalid input")
        
        message = self.error_handler.create_user_friendly_message(error, "processing data")
        
        assert "processing data" in message
        assert "contact support" in message.lower()
    
    def test_wrap_operation_success(self):
        """Test wrapping successful operation."""
        def successful_operation():
            return "operation completed"
        
        result = self.error_handler.wrap_operation(
            successful_operation,
            "test operation",
            operation_id="test_123"
        )
        
        assert result == "operation completed"
    
    def test_wrap_operation_with_error_user_friendly(self):
        """Test wrapping operation that fails with user-friendly error handling."""
        def failing_operation():
            raise ConnectionError("Network failed")
        
        result = self.error_handler.wrap_operation(
            failing_operation,
            "network operation",
            user_friendly_errors=True
        )
        
        # Should return user-friendly error message, not raise exception
        assert isinstance(result, str)
        assert "connection error" in result.lower()
    
    def test_wrap_operation_with_error_raise_exception(self):
        """Test wrapping operation that fails and re-raises exception."""
        def failing_operation():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            self.error_handler.wrap_operation(
                failing_operation,
                "test operation",
                user_friendly_errors=False
            )
    
    def test_wrap_operation_with_partial_results_preservation(self):
        """Test wrapping operation with partial results preservation."""
        def failing_operation_with_partial():
            # Simulate an operation that has partial results
            failing_operation_with_partial.partial_results = {"processed": 5}
            raise Exception("Operation failed")
        
        result = self.error_handler.wrap_operation(
            failing_operation_with_partial,
            "batch operation",
            operation_id="batch_123",
            preserve_partial=True,
            user_friendly_errors=True
        )
        
        # Should preserve partial results
        assert self.error_handler.has_partial_results("batch_123")
        partial = self.error_handler.get_partial_results("batch_123")
        assert partial == {"processed": 5}
        
        # Should return user-friendly error message
        assert isinstance(result, str)