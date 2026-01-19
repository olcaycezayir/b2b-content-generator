"""
Utility Module for B2B AI E-commerce Content Generator

This module contains common utilities including data validation,
configuration management, and error handling.
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from io import BytesIO
import pandas as pd
import logging
import os
import re

if TYPE_CHECKING:
    from utils import ConfigurationManager


@dataclass
class ValidationResult:
    """Result of data validation operations."""
    is_valid: bool
    errors: List[str]
    warnings: List[str] = field(default_factory=list)


@dataclass
class ProcessingProgress:
    """Progress tracking for long-running operations."""
    current: int
    total: int
    status: str
    errors: List[str] = field(default_factory=list)


@dataclass
class ProductInput:
    """Input data for product content generation."""
    name: Optional[str] = None
    image_data: Optional[bytes] = None
    additional_attributes: Dict[str, str] = field(default_factory=dict)

    def validate(self) -> ValidationResult:
        """Validate product input data."""
        errors = []
        warnings = []
        
        # Check that at least one input method is provided
        if not self.name and not self.image_data:
            errors.append("Either product name or image data must be provided")
        
        # Validate product name if provided
        if self.name is not None:
            if not isinstance(self.name, str):
                errors.append("Product name must be a string")
            elif len(self.name.strip()) == 0:
                errors.append("Product name cannot be empty")
            elif len(self.name) > 200:
                warnings.append("Product name is very long (>200 characters)")
        
        # Validate image data if provided
        if self.image_data is not None:
            if not isinstance(self.image_data, bytes):
                errors.append("Image data must be bytes")
            elif len(self.image_data) == 0:
                errors.append("Image data cannot be empty")
        
        # Validate additional attributes
        if self.additional_attributes:
            for key, value in self.additional_attributes.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    errors.append(f"Additional attribute '{key}' must have string key and value")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


@dataclass
class ProductContent:
    """Generated product content including title, description, and hashtags."""
    title: str
    description: str
    hashtags: List[str]

    def validate(self) -> ValidationResult:
        """Validate generated product content meets requirements."""
        errors = []
        warnings = []
        
        # Validate title (≤60 characters)
        if not isinstance(self.title, str):
            errors.append("Title must be a string")
        elif len(self.title) == 0:
            errors.append("Title cannot be empty")
        elif len(self.title) > 60:
            errors.append(f"Title must be ≤60 characters (current: {len(self.title)})")
        
        # Validate description (100-300 words)
        if not isinstance(self.description, str):
            errors.append("Description must be a string")
        elif len(self.description.strip()) == 0:
            errors.append("Description cannot be empty")
        else:
            # Count words in description
            word_count = len(self.description.split())
            if word_count < 100:
                errors.append(f"Description must be at least 100 words (current: {word_count})")
            elif word_count > 300:
                errors.append(f"Description must be at most 300 words (current: {word_count})")
        
        # Validate hashtags (exactly 5)
        if not isinstance(self.hashtags, list):
            errors.append("Hashtags must be a list")
        elif len(self.hashtags) != 5:
            errors.append(f"Must have exactly 5 hashtags (current: {len(self.hashtags)})")
        else:
            for i, hashtag in enumerate(self.hashtags):
                if not isinstance(hashtag, str):
                    errors.append(f"Hashtag {i+1} must be a string")
                elif not hashtag.startswith('#'):
                    errors.append(f"Hashtag {i+1} must start with '#'")
                elif len(hashtag) < 2:
                    errors.append(f"Hashtag {i+1} is too short")
                elif len(hashtag) > 30:
                    warnings.append(f"Hashtag {i+1} is very long (>30 characters)")
                elif not re.match(r'^#[a-zA-Z0-9_]+$', hashtag):
                    errors.append(f"Hashtag {i+1} contains invalid characters (only letters, numbers, and underscores allowed)")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def word_count(self) -> int:
        """Get word count of the description."""
        return len(self.description.split())


class DataValidator:
    """Validator for input data and file operations."""
    
    # Maximum file size: 50MB
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Required CSV columns
    REQUIRED_CSV_COLUMNS = ['product_name']
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'.csv', '.tsv'}
    
    def validate_product_input(self, input_data: Any) -> ValidationResult:
        """Validate product input data."""
        if not isinstance(input_data, ProductInput):
            return ValidationResult(
                is_valid=False,
                errors=["Input must be a ProductInput instance"]
            )
        
        return input_data.validate()
    
    def sanitize_text_input(self, text: str) -> str:
        """Sanitize text input to prevent injection attacks."""
        if not isinstance(text, str):
            return ""
        
        # Remove potential script tags and other dangerous content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
        text = re.sub(r'javascript:\s*', '', text, flags=re.IGNORECASE)  # Remove javascript: URLs
        text = re.sub(r'on\w+\s*=\s*[^>\s]*', '', text, flags=re.IGNORECASE)  # Remove event handlers
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def validate_file_size(self, file_buffer: BytesIO) -> bool:
        """Validate uploaded file size."""
        if not isinstance(file_buffer, BytesIO):
            return False
        
        # Get current position and seek to end to get size
        current_pos = file_buffer.tell()
        file_buffer.seek(0, 2)  # Seek to end
        size = file_buffer.tell()
        file_buffer.seek(current_pos)  # Restore position
        
        return size <= self.MAX_FILE_SIZE
    
    def validate_csv_columns(self, df: pd.DataFrame) -> List[str]:
        """Validate CSV columns and return missing required columns."""
        if not isinstance(df, pd.DataFrame):
            return self.REQUIRED_CSV_COLUMNS
        
        missing_columns = []
        for required_col in self.REQUIRED_CSV_COLUMNS:
            if required_col not in df.columns:
                missing_columns.append(required_col)
        
        return missing_columns
    
    def validate_csv_format(self, df: pd.DataFrame) -> ValidationResult:
        """Comprehensive CSV format validation."""
        errors = []
        warnings = []
        
        if not isinstance(df, pd.DataFrame):
            return ValidationResult(
                is_valid=False,
                errors=["Input must be a pandas DataFrame"]
            )
        
        # Check for required columns
        missing_columns = self.validate_csv_columns(df)
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Check if DataFrame is empty
        if df.empty:
            errors.append("CSV file is empty")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Validate data types and content
        if 'product_name' in df.columns:
            # Check for null/empty product names
            null_names = df['product_name'].isnull().sum()
            if null_names > 0:
                warnings.append(f"{null_names} rows have missing product names")
            
            # Check for very long product names
            long_names = (df['product_name'].str.len() > 200).sum()
            if long_names > 0:
                warnings.append(f"{long_names} rows have very long product names (>200 characters)")
        
        # Check total row count
        if len(df) > 10000:
            warnings.append(f"Large file with {len(df)} rows - processing may take time")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_file_extension(self, filename: str) -> bool:
        """Validate file extension is allowed."""
        if not isinstance(filename, str):
            return False
        
        _, ext = os.path.splitext(filename.lower())
        return ext in self.ALLOWED_EXTENSIONS


class ConfigurationManager:
    """Manager for application configuration and environment variables."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.config = {}
        self._load_environment_config()
    
    def _load_environment_config(self) -> Dict[str, str]:
        """Load configuration from environment variables."""
        from dotenv import load_dotenv
        
        # Load .env file if it exists
        load_dotenv()
        
        # Define configuration keys and their default values
        config_keys = {
            'OPENAI_API_KEY': None,  # Required, no default
            'APP_ENV': 'development',
            'DEBUG': 'true',
            'MAX_FILE_SIZE_MB': '50',
            'CSV_CHUNK_SIZE': '100',
            'MAX_RETRIES': '3',
            'RETRY_DELAY_BASE': '1.0',
            'RATE_LIMIT_DELAY': '60'
        }
        
        # Load configuration from environment
        for key, default_value in config_keys.items():
            env_value = os.getenv(key, default_value)
            self.config[key] = env_value
        
        return self.config
    
    def validate_api_key(self) -> bool:
        """Validate OpenAI API key is present and valid."""
        api_key = self.config.get('OPENAI_API_KEY')
        
        # Check if API key exists
        if not api_key:
            return False
        
        # Check if API key is not the placeholder value
        if api_key == 'your_openai_api_key_here':
            return False
        
        # Basic format validation (OpenAI keys start with 'sk-')
        if not api_key.startswith('sk-'):
            return False
        
        # Check minimum length (OpenAI keys are typically 51+ characters)
        if len(api_key) < 20:
            return False
        
        return True
    
    def get_openai_client(self):
        """Get configured OpenAI client."""
        from openai import OpenAI
        
        if not self.validate_api_key():
            raise ValueError("Invalid or missing OpenAI API key. Please check your configuration.")
        
        # Create OpenAI client with API key
        client = OpenAI(api_key=self.config['OPENAI_API_KEY'])
        return client
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return self.config.get(key, default)
    
    def get_int_config(self, key: str, default: int = 0) -> int:
        """Get configuration value as integer."""
        value = self.config.get(key, str(default))
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_float_config(self, key: str, default: float = 0.0) -> float:
        """Get configuration value as float."""
        value = self.config.get(key, str(default))
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_bool_config(self, key: str, default: bool = False) -> bool:
        """Get configuration value as boolean."""
        # Get the value from environment first, then from config
        value = os.getenv(key, self.config.get(key, str(default))).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.get_config_value('APP_ENV', 'development').lower() == 'development'
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.get_config_value('APP_ENV', 'development').lower() == 'production'
    
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.get_config_value('APP_ENV', 'development').lower() == 'test'
    
    def get_setup_instructions(self) -> str:
        """Get setup instructions for missing configuration."""
        instructions = []
        
        if not self.validate_api_key():
            instructions.append(
                "1. OpenAI API Key is missing or invalid:\n"
                "   - Sign up at https://platform.openai.com/\n"
                "   - Generate an API key in your account settings\n"
                "   - Set the OPENAI_API_KEY environment variable or add it to your .env file\n"
                "   - Example: OPENAI_API_KEY=sk-your-actual-key-here"
            )
        
        if not instructions:
            return "Configuration is complete! All required settings are properly configured."
        
        return (
            "Configuration Setup Required:\n\n" +
            "\n\n".join(instructions) +
            "\n\nFor more details, see the setup_instructions.md file."
        )
    
    def validate_configuration(self) -> ValidationResult:
        """Validate all configuration settings."""
        errors = []
        warnings = []
        
        # Validate API key
        if not self.validate_api_key():
            errors.append("OpenAI API key is missing or invalid")
        
        # Validate numeric configurations
        try:
            max_file_size = self.get_int_config('MAX_FILE_SIZE_MB', 50)
            if max_file_size <= 0:
                errors.append("MAX_FILE_SIZE_MB must be a positive integer")
            elif max_file_size > 500:
                warnings.append("MAX_FILE_SIZE_MB is very large (>500MB)")
        except (ValueError, TypeError):
            errors.append("MAX_FILE_SIZE_MB must be a valid integer")
        
        # Check CSV_CHUNK_SIZE specifically for invalid values
        chunk_size_str = os.getenv('CSV_CHUNK_SIZE', self.config.get('CSV_CHUNK_SIZE', '100'))
        try:
            chunk_size = int(chunk_size_str)
            if chunk_size <= 0:
                errors.append("CSV_CHUNK_SIZE must be a positive integer")
            elif chunk_size > 10000:
                warnings.append("CSV_CHUNK_SIZE is very large (>10000)")
        except (ValueError, TypeError):
            errors.append("CSV_CHUNK_SIZE must be a valid integer")
        
        # Check MAX_RETRIES specifically for invalid values
        max_retries_str = os.getenv('MAX_RETRIES', self.config.get('MAX_RETRIES', '3'))
        try:
            max_retries = int(max_retries_str)
            if max_retries < 0:
                errors.append("MAX_RETRIES must be non-negative")
            elif max_retries > 10:
                warnings.append("MAX_RETRIES is very high (>10)")
        except (ValueError, TypeError):
            errors.append("MAX_RETRIES must be a valid integer")
        
        # Check RETRY_DELAY_BASE specifically for invalid values
        retry_delay_str = os.getenv('RETRY_DELAY_BASE', self.config.get('RETRY_DELAY_BASE', '1.0'))
        try:
            retry_delay = float(retry_delay_str)
            if retry_delay < 0:
                errors.append("RETRY_DELAY_BASE must be non-negative")
        except (ValueError, TypeError):
            errors.append("RETRY_DELAY_BASE must be a valid number")
        
        # Validate environment
        app_env = self.get_config_value('APP_ENV', 'development').lower()
        valid_envs = {'development', 'production', 'test'}
        if app_env not in valid_envs:
            warnings.append(f"APP_ENV '{app_env}' is not a standard environment. Valid options: {', '.join(valid_envs)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def get_safe_config_summary(self) -> Dict[str, str]:
        """Get configuration summary with sensitive data masked."""
        safe_config = {}
        
        for key, value in self.config.items():
            if 'key' in key.lower() or 'secret' in key.lower() or 'password' in key.lower():
                # Mask sensitive values
                if value and len(value) > 4:
                    safe_config[key] = f"{value[:4]}{'*' * (len(value) - 4)}"
                else:
                    safe_config[key] = "***" if value else "Not set"
            else:
                safe_config[key] = value or "Not set"
        
        return safe_config


class ErrorHandler:
    """Handler for application errors and recovery."""
    
    def __init__(self, config_manager: Optional['ConfigurationManager'] = None):
        """Initialize error handler."""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager or ConfigurationManager()
        self.partial_results = {}  # Store partial results for recovery
        
        # Configure logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        # Only configure if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
            # Set log level based on environment
            if self.config_manager.is_development():
                self.logger.setLevel(logging.DEBUG)
            else:
                self.logger.setLevel(logging.INFO)
    
    def retry_with_exponential_backoff(
        self,
        func: callable,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        max_delay: float = 300.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = None
    ) -> Any:
        """
        Retry a function with exponential backoff.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds (doubles each retry)
            max_delay: Maximum delay between retries
            backoff_factor: Multiplier for delay (default 2.0 for exponential)
            jitter: Add random jitter to prevent thundering herd
            retryable_exceptions: Tuple of exception types to retry on
        
        Returns:
            Result of successful function call
            
        Raises:
            Last exception if all retries exhausted
        """
        import time
        import random
        
        # Get configuration values
        if max_retries is None:
            max_retries = self.config_manager.get_int_config('MAX_RETRIES', 3)
        if base_delay is None:
            base_delay = self.config_manager.get_float_config('RETRY_DELAY_BASE', 1.0)
        
        # Default retryable exceptions (network and API errors)
        if retryable_exceptions is None:
            retryable_exceptions = (
                ConnectionError,
                TimeoutError,
                OSError,  # Includes network-related OS errors
                Exception  # Catch-all for API errors - will be refined in practice
            )
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                result = func()
                
                # Log successful retry if this wasn't the first attempt
                if attempt > 0:
                    self.logger.info(f"Function succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if this exception type should be retried
                if not isinstance(e, retryable_exceptions):
                    self.logger.error(f"Non-retryable exception: {type(e).__name__}: {e}")
                    raise e
                
                # If this was the last attempt, don't wait
                if attempt >= max_retries:
                    break
                
                # Calculate delay with exponential backoff
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                
                # Add jitter to prevent thundering herd problem
                if jitter:
                    delay *= (0.5 + random.random() * 0.5)  # Random factor between 0.5 and 1.0
                
                self.logger.warning(
                    f"Attempt {attempt + 1} failed with {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                
                # Log detailed error information for debugging
                self.log_error(e, f"Retry attempt {attempt + 1}/{max_retries + 1}")
                
                time.sleep(delay)
        
        # All retries exhausted
        self.logger.error(f"All {max_retries + 1} attempts failed. Last error: {last_exception}")
        raise last_exception
    
    def handle_api_error(self, error: Exception, context: str = "") -> str:
        """
        Handle API-related errors and return user-friendly message.
        
        Args:
            error: The exception that occurred
            context: Additional context about when the error occurred
            
        Returns:
            User-friendly error message
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # Log the detailed error for debugging
        self.log_error(error, f"API Error - {context}")
        
        # Handle specific API error types
        if "rate limit" in error_message.lower() or ("quota" in error_message.lower() and "exceeded" in error_message.lower()):
            return (
                "⚠️ API rate limit exceeded. Please wait a moment and try again. "
                "If this persists, consider upgrading your OpenAI plan or reducing the batch size."
            )
        
        elif "authentication" in error_message.lower() or "api key" in error_message.lower():
            return (
                "🔑 Authentication failed. Please check your OpenAI API key configuration. "
                "Make sure your API key is valid and has sufficient permissions."
            )
        
        elif "insufficient" in error_message.lower() and "quota" in error_message.lower():
            return (
                "💳 Insufficient API quota. Please check your OpenAI account billing and usage limits. "
                "You may need to add credits or upgrade your plan."
            )
        
        elif "timeout" in error_message.lower() or isinstance(error, TimeoutError):
            return (
                "⏱️ Request timed out. The AI service is taking longer than expected. "
                "Please try again with a smaller batch or check your internet connection."
            )
        
        elif "connection" in error_message.lower() or isinstance(error, ConnectionError):
            return (
                "🌐 Connection error. Please check your internet connection and try again. "
                "If the problem persists, the OpenAI service may be temporarily unavailable."
            )
        
        elif "model" in error_message.lower() and "not found" in error_message.lower():
            return (
                "🤖 The requested AI model is not available. Please check your OpenAI account "
                "permissions or contact support if you believe this is an error."
            )
        
        else:
            # Generic API error
            return (
                f"❌ An unexpected error occurred while communicating with the AI service: {error_type}. "
                "Please try again, and if the problem persists, contact support."
            )
    
    def handle_file_error(self, error: Exception, context: str = "") -> str:
        """
        Handle file operation errors and return user-friendly message.
        
        Args:
            error: The exception that occurred
            context: Additional context about when the error occurred
            
        Returns:
            User-friendly error message
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # Log the detailed error for debugging
        self.log_error(error, f"File Error - {context}")
        
        # Handle specific file error types
        if isinstance(error, FileNotFoundError):
            return (
                "📁 File not found. Please make sure the file exists and you have "
                "permission to access it."
            )
        
        elif isinstance(error, PermissionError):
            return (
                "🔒 Permission denied. Please check that you have the necessary "
                "permissions to read/write this file."
            )
        
        elif "memory" in error_message.lower() or isinstance(error, MemoryError):
            return (
                "💾 File is too large to process. Please try with a smaller file "
                "or contact support for assistance with large datasets."
            )
        
        elif "csv" in error_message.lower() or "parse" in error_message.lower():
            return (
                "📊 Invalid CSV format. Please ensure your file is a valid CSV with "
                "proper formatting and required columns (product_name)."
            )
        
        elif "encoding" in error_message.lower() or "decode" in error_message.lower():
            return (
                "🔤 File encoding error. Please save your CSV file with UTF-8 encoding "
                "and try again."
            )
        
        elif "size" in error_message.lower() and "limit" in error_message.lower():
            return (
                "📏 File size exceeds the maximum limit (50MB). Please reduce the file size "
                "or split it into smaller files."
            )
        
        else:
            # Generic file error
            return (
                f"📄 File processing error ({error_type}). Please check your file format "
                "and try again. If the problem persists, contact support."
            )
    
    def handle_validation_error(self, validation_result: ValidationResult, context: str = "") -> str:
        """
        Handle validation errors and return user-friendly message.
        
        Args:
            validation_result: ValidationResult with errors and warnings
            context: Additional context about what was being validated
            
        Returns:
            User-friendly error message
        """
        if validation_result.is_valid:
            return ""
        
        # Log validation errors
        self.logger.warning(f"Validation failed - {context}: {validation_result.errors}")
        
        error_messages = []
        
        # Format errors in a user-friendly way
        if validation_result.errors:
            error_messages.append("❌ **Validation Errors:**")
            for error in validation_result.errors:
                error_messages.append(f"   • {error}")
        
        # Include warnings if present
        if validation_result.warnings:
            error_messages.append("⚠️ **Warnings:**")
            for warning in validation_result.warnings:
                error_messages.append(f"   • {warning}")
        
        return "\n".join(error_messages)
    
    def preserve_partial_results(self, operation_id: str, results: Any) -> None:
        """
        Preserve partial results for recovery scenarios.
        
        Args:
            operation_id: Unique identifier for the operation
            results: Partial results to preserve
        """
        self.partial_results[operation_id] = {
            'results': results,
            'timestamp': pd.Timestamp.now(),
            'status': 'partial'
        }
        
        self.logger.info(f"Preserved partial results for operation: {operation_id}")
    
    def get_partial_results(self, operation_id: str) -> Optional[Any]:
        """
        Retrieve preserved partial results.
        
        Args:
            operation_id: Unique identifier for the operation
            
        Returns:
            Partial results if available, None otherwise
        """
        if operation_id in self.partial_results:
            return self.partial_results[operation_id]['results']
        return None
    
    def clear_partial_results(self, operation_id: str) -> None:
        """
        Clear partial results after successful completion.
        
        Args:
            operation_id: Unique identifier for the operation
        """
        if operation_id in self.partial_results:
            del self.partial_results[operation_id]
            self.logger.info(f"Cleared partial results for operation: {operation_id}")
    
    def has_partial_results(self, operation_id: str) -> bool:
        """
        Check if partial results exist for an operation.
        
        Args:
            operation_id: Unique identifier for the operation
            
        Returns:
            True if partial results exist, False otherwise
        """
        return operation_id in self.partial_results
    
    def get_recovery_options(self, operation_id: str) -> Dict[str, Any]:
        """
        Get recovery options for a failed operation.
        
        Args:
            operation_id: Unique identifier for the operation
            
        Returns:
            Dictionary with recovery options and information
        """
        if not self.has_partial_results(operation_id):
            return {
                'can_recover': False,
                'message': 'No partial results available for recovery.'
            }
        
        partial_data = self.partial_results[operation_id]
        
        return {
            'can_recover': True,
            'timestamp': partial_data['timestamp'],
            'status': partial_data['status'],
            'message': (
                f"Partial results from {partial_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} "
                "are available. You can resume processing from where it left off."
            ),
            'resume_available': True
        }
    
    def log_error(self, error: Exception, context: str) -> None:
        """
        Log error with detailed debugging information.
        
        Args:
            error: The exception that occurred
            context: Additional context about when/where the error occurred
        """
        import traceback
        
        # Create detailed error information
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'timestamp': pd.Timestamp.now().isoformat(),
        }
        
        # Add traceback in development mode
        if self.config_manager.is_development():
            error_info['traceback'] = traceback.format_exc()
        
        # Log at appropriate level
        if isinstance(error, (ConnectionError, TimeoutError)):
            # Network errors are often temporary - log as warning
            self.logger.warning(f"Network error in {context}: {error_info}")
        else:
            # Other errors are more serious - log as error
            self.logger.error(f"Error in {context}: {error_info}")
        
        # In production, also log to a structured format for monitoring
        if self.config_manager.is_production():
            # This could be extended to send to external monitoring services
            self.logger.error(f"STRUCTURED_ERROR: {error_info}")
    
    def create_user_friendly_message(
        self,
        error: Exception,
        operation: str,
        suggestions: List[str] = None
    ) -> str:
        """
        Create a comprehensive user-friendly error message.
        
        Args:
            error: The exception that occurred
            operation: Description of what operation was being performed
            suggestions: List of suggested actions for the user
            
        Returns:
            Formatted user-friendly error message
        """
        # Get base error message based on error type
        if hasattr(error, '__class__') and 'api' in error.__class__.__module__.lower():
            base_message = self.handle_api_error(error, operation)
        elif isinstance(error, (ConnectionError, TimeoutError)):
            base_message = self.handle_api_error(error, operation)
        elif isinstance(error, (FileNotFoundError, PermissionError, IOError)):
            base_message = self.handle_file_error(error, operation)
        else:
            base_message = f"❌ An error occurred during {operation}: {type(error).__name__}"
        
        # Build complete message
        message_parts = [base_message]
        
        # Add suggestions if provided
        if suggestions:
            message_parts.append("\n💡 **Suggestions:**")
            for suggestion in suggestions:
                message_parts.append(f"   • {suggestion}")
        
        # Add general help
        message_parts.append(
            "\n🆘 If the problem persists, please check the logs or contact support."
        )
        
        return "\n".join(message_parts)
    
    def wrap_operation(
        self,
        operation_func: callable,
        operation_name: str,
        operation_id: str = None,
        preserve_partial: bool = False,
        user_friendly_errors: bool = True
    ) -> Any:
        """
        Wrap an operation with comprehensive error handling.
        
        Args:
            operation_func: Function to execute
            operation_name: Human-readable name for the operation
            operation_id: Unique identifier for partial result preservation
            preserve_partial: Whether to preserve partial results on failure
            user_friendly_errors: Whether to convert errors to user-friendly messages
            
        Returns:
            Result of the operation or user-friendly error message
        """
        try:
            result = operation_func()
            
            # Clear any partial results on success
            if operation_id and self.has_partial_results(operation_id):
                self.clear_partial_results(operation_id)
            
            return result
            
        except Exception as e:
            # Log the error
            self.log_error(e, f"Operation: {operation_name}")
            
            # Preserve partial results if requested and available
            if preserve_partial and operation_id and hasattr(operation_func, 'partial_results'):
                self.preserve_partial_results(operation_id, operation_func.partial_results)
            
            # Return user-friendly error or re-raise
            if user_friendly_errors:
                return self.create_user_friendly_message(e, operation_name)
            else:
                raise