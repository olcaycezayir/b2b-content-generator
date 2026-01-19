"""
Unit tests for LLMService class.

Tests the OpenAI integration, retry logic, rate limiting, and response validation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from llm_service import LLMService
from utils import ConfigurationManager


class TestLLMService:
    """Test cases for LLMService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock configuration manager
        self.mock_config = Mock(spec=ConfigurationManager)
        self.mock_config.get_int_config.return_value = 3  # max_retries
        self.mock_config.get_float_config.return_value = 1.0  # retry_delay_base
        self.mock_config.validate_api_key.return_value = True
        
        # Create mock OpenAI client
        self.mock_client = Mock()
        self.mock_config.get_openai_client.return_value = self.mock_client
    
    def create_mock_response(self, content="Test response", finish_reason="stop"):
        """Create a mock ChatCompletion response."""
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = content
        
        mock_choice = Mock(spec=Choice)
        mock_choice.message = mock_message
        mock_choice.finish_reason = finish_reason
        
        mock_usage = Mock(spec=CompletionUsage)
        mock_usage.total_tokens = 100
        
        mock_response = Mock(spec=ChatCompletion)
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        
        return mock_response
    
    def test_initialization_success(self):
        """Test successful LLMService initialization."""
        service = LLMService(self.mock_config)
        
        assert service.config_manager == self.mock_config
        assert service.client == self.mock_client
        assert service.MODEL_NAME == "gpt-4o"
        self.mock_config.get_openai_client.assert_called_once()
    
    def test_initialization_failure(self):
        """Test LLMService initialization failure."""
        self.mock_config.get_openai_client.side_effect = ValueError("Invalid API key")
        
        with pytest.raises(ValueError, match="OpenAI client initialization failed"):
            LLMService(self.mock_config)
    
    def test_generate_content_success(self):
        """Test successful content generation."""
        service = LLMService(self.mock_config)
        
        # Mock successful API response
        mock_response = self.create_mock_response("Generated content")
        self.mock_client.chat.completions.create.return_value = mock_response
        
        result = service.generate_content("Test prompt")
        
        assert result == "Generated content"
        self.mock_client.chat.completions.create.assert_called_once()
        
        # Verify API call parameters
        call_args = self.mock_client.chat.completions.create.call_args
        assert call_args[1]['model'] == "gpt-4o"
        assert len(call_args[1]['messages']) == 2
        assert call_args[1]['messages'][1]['content'] == "Test prompt"
    
    def test_generate_content_invalid_prompt(self):
        """Test content generation with invalid prompt."""
        service = LLMService(self.mock_config)
        
        # Test empty prompt
        with pytest.raises(ValueError, match="Prompt must be a non-empty string"):
            service.generate_content("")
        
        # Test None prompt
        with pytest.raises(ValueError, match="Prompt must be a non-empty string"):
            service.generate_content(None)
        
        # Test non-string prompt
        with pytest.raises(ValueError, match="Prompt must be a non-empty string"):
            service.generate_content(123)
    
    def test_generate_content_client_not_initialized(self):
        """Test content generation when client is not initialized."""
        service = LLMService(self.mock_config)
        service.client = None
        
        with pytest.raises(ValueError, match="OpenAI client not initialized"):
            service.generate_content("Test prompt")
    
    def test_api_response_validation_success(self):
        """Test successful API response validation."""
        service = LLMService(self.mock_config)
        
        # Valid response
        mock_response = self.create_mock_response("Valid content")
        assert service._validate_api_response(mock_response) is True
    
    def test_api_response_validation_failures(self):
        """Test API response validation failures."""
        service = LLMService(self.mock_config)
        
        # Invalid response type
        assert service._validate_api_response("invalid") is False
        
        # Missing choices
        mock_response = Mock()
        mock_response.choices = []
        assert service._validate_api_response(mock_response) is False
        
        # Missing message
        mock_response = Mock()
        mock_choice = Mock()
        mock_response.choices = [mock_choice]
        assert service._validate_api_response(mock_response) is False
        
        # None content
        mock_response = self.create_mock_response(None)
        assert service._validate_api_response(mock_response) is False
    
    def test_retry_logic_success_after_failure(self):
        """Test retry logic succeeds after initial failure."""
        service = LLMService(self.mock_config)
        
        # First call fails, second succeeds
        mock_response = self.create_mock_response("Success after retry")
        self.mock_client.chat.completions.create.side_effect = [
            ConnectionError("Network error"),
            mock_response
        ]
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = service.generate_content("Test prompt")
        
        assert result == "Success after retry"
        assert self.mock_client.chat.completions.create.call_count == 2
    
    def test_retry_logic_max_retries_exceeded(self):
        """Test retry logic when max retries are exceeded."""
        service = LLMService(self.mock_config)
        
        # All calls fail
        self.mock_client.chat.completions.create.side_effect = ConnectionError("Persistent error")
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(ConnectionError, match="Persistent error"):
                service.generate_content("Test prompt")
        
        # Should try initial + 3 retries = 4 total attempts
        assert self.mock_client.chat.completions.create.call_count == 4
    
    def test_rate_limit_handling(self):
        """Test rate limit error handling."""
        service = LLMService(self.mock_config)
        
        # Mock rate limit delay configuration
        self.mock_config.get_float_config.side_effect = lambda key, default: {
            'RETRY_DELAY_BASE': 1.0,
            'RATE_LIMIT_DELAY': 60.0
        }.get(key, default)
        
        # First call hits rate limit, second succeeds
        mock_response = self.create_mock_response("Success after rate limit")
        rate_limit_error = Exception("Rate limit exceeded")
        self.mock_client.chat.completions.create.side_effect = [
            rate_limit_error,
            mock_response
        ]
        
        with patch('time.sleep') as mock_sleep:
            result = service.generate_content("Test prompt")
        
        assert result == "Success after rate limit"
        # Should have slept for rate limit delay
        mock_sleep.assert_called()
        # Verify the delay was calculated correctly (should be around 60 seconds with jitter)
        sleep_call_args = mock_sleep.call_args[0][0]
        assert 48 <= sleep_call_args <= 72  # 60 * (0.8 to 1.2 jitter range)
    
    def test_rate_limit_delay_calculation(self):
        """Test rate limit delay calculation."""
        service = LLMService(self.mock_config)
        
        # Mock configuration
        self.mock_config.get_float_config.return_value = 60.0  # base delay
        
        with patch('random.uniform', return_value=1.0):  # No jitter for predictable test
            # Test exponential backoff
            delay_0 = service._handle_rate_limit(0)
            delay_1 = service._handle_rate_limit(1)
            delay_2 = service._handle_rate_limit(2)
            
            assert delay_0 == 60.0  # 60 * 2^0 * 1.0
            assert delay_1 == 120.0  # 60 * 2^1 * 1.0
            assert delay_2 == 240.0  # 60 * 2^2 * 1.0
            
            # Test maximum delay cap
            delay_high = service._handle_rate_limit(10)
            assert delay_high == 600.0  # Capped at 10 minutes
    
    def test_non_retryable_error(self):
        """Test handling of non-retryable errors."""
        service = LLMService(self.mock_config)
        
        # Authentication error should not be retried
        auth_error = Exception("Invalid API key")
        self.mock_client.chat.completions.create.side_effect = auth_error
        
        with pytest.raises(Exception, match="Invalid API key"):
            service.generate_content("Test prompt")
        
        # Should only try once (no retries for non-retryable errors)
        assert self.mock_client.chat.completions.create.call_count == 1
    
    def test_get_model_info(self):
        """Test getting model information."""
        service = LLMService(self.mock_config)
        
        info = service.get_model_info()
        
        assert info['model_name'] == "gpt-4o"
        assert info['max_tokens'] == 1000
        assert info['temperature'] == 0.7
        assert info['client_initialized'] is True
        assert info['api_key_configured'] is True
    
    def test_test_connection_success(self):
        """Test successful connection test."""
        service = LLMService(self.mock_config)
        
        # Mock successful response
        mock_response = self.create_mock_response("Hello")
        self.mock_client.chat.completions.create.return_value = mock_response
        
        result = service.test_connection()
        
        assert result is True
        self.mock_client.chat.completions.create.assert_called_once()
    
    def test_test_connection_failure(self):
        """Test connection test failure."""
        service = LLMService(self.mock_config)
        
        # Mock API error
        self.mock_client.chat.completions.create.side_effect = Exception("Connection failed")
        
        result = service.test_connection()
        
        assert result is False
    
    def test_empty_response_handling(self):
        """Test handling of empty API responses."""
        service = LLMService(self.mock_config)
        
        # Mock empty response
        mock_response = self.create_mock_response("")
        self.mock_client.chat.completions.create.return_value = mock_response
        
        with pytest.raises(ValueError, match="Empty content received from API"):
            service.generate_content("Test prompt")
    
    def test_whitespace_prompt_handling(self):
        """Test handling of whitespace-only prompts."""
        service = LLMService(self.mock_config)
        
        with pytest.raises(ValueError, match="Prompt cannot be empty after sanitization"):
            service.generate_content("   \n\t   ")
    
    def test_high_token_usage_warning(self):
        """Test warning for high token usage."""
        service = LLMService(self.mock_config)
        
        # Create response with high token usage
        mock_response = self.create_mock_response("Test content")
        mock_response.usage.total_tokens = 5000  # High usage
        
        # Should still validate successfully but log warning
        assert service._validate_api_response(mock_response) is True


# Integration test with real configuration
class TestLLMServiceIntegration:
    """Integration tests for LLMService with real ConfigurationManager."""
    
    def test_initialization_with_real_config(self):
        """Test initialization with real ConfigurationManager."""
        # This test requires a valid API key in environment
        config = ConfigurationManager()
        
        if not config.validate_api_key():
            pytest.skip("No valid OpenAI API key configured")
        
        service = LLMService(config)
        
        assert service.client is not None
        assert service.config_manager == config
        
        # Test model info
        info = service.get_model_info()
        assert info['client_initialized'] is True
        assert info['api_key_configured'] is True