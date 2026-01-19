"""
LLM Service Module for B2B AI E-commerce Content Generator

This module handles all interactions with the OpenAI API, including
retry logic, rate limiting, and response validation.
"""

from typing import Any, Optional, TYPE_CHECKING
import time
import logging
import json
import random

if TYPE_CHECKING:
    from utils import ConfigurationManager, ErrorHandler

# Import OpenAI with error handling for missing dependency
try:
    from openai import OpenAI
    from openai.types.chat import ChatCompletion
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    ChatCompletion = None
    OPENAI_AVAILABLE = False


class LLMService:
    """Service for interacting with OpenAI's LLM API."""
    
    # GPT-4o model specification as required
    MODEL_NAME = "gpt-4o"
    
    # Default parameters for content generation
    DEFAULT_MAX_TOKENS = 1000
    DEFAULT_TEMPERATURE = 0.7
    
    def __init__(self, config_manager: 'ConfigurationManager'):
        """Initialize LLM service with configuration manager."""
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI library is not available. Please install it with: pip install openai"
            )
        
        self.config_manager = config_manager
        self.client: Optional[OpenAI] = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize client
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize OpenAI client using configuration manager."""
        try:
            # Get OpenAI client from configuration manager
            # This handles API key validation and client creation
            self.client = self.config_manager.get_openai_client()
            self.logger.info("OpenAI client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ValueError(f"OpenAI client initialization failed: {e}")
    
    def generate_content(self, prompt: str) -> str:
        """
        Generate content using OpenAI GPT-4o model.
        
        Args:
            prompt: The prompt to send to the AI model
            
        Returns:
            Generated content as string
            
        Raises:
            ValueError: If prompt is invalid or client not initialized
            Exception: If API call fails after all retries
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized")
        
        if not prompt or not isinstance(prompt, str):
            raise ValueError("Prompt must be a non-empty string")
        
        # Sanitize prompt to prevent potential issues
        prompt = prompt.strip()
        if len(prompt) == 0:
            raise ValueError("Prompt cannot be empty after sanitization")
        
        # Make API call with retry logic
        try:
            response_content = self._make_api_call_with_retry(prompt)
            return response_content
            
        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            raise
    
    def _make_api_call_with_retry(self, prompt: str, max_retries: Optional[int] = None) -> str:
        """
        Make API call with retry logic and exponential backoff.
        
        Args:
            prompt: The prompt to send to the API
            max_retries: Maximum number of retry attempts (uses config if None)
            
        Returns:
            Generated content from the API
            
        Raises:
            Exception: If all retry attempts fail
        """
        if max_retries is None:
            max_retries = self.config_manager.get_int_config('MAX_RETRIES', 3)
        
        base_delay = self.config_manager.get_float_config('RETRY_DELAY_BASE', 1.0)
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Make the actual API call
                response = self.client.chat.completions.create(
                    model=self.MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert e-commerce content generator. Generate high-quality, SEO-optimized product content."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    max_tokens=self.DEFAULT_MAX_TOKENS,
                    temperature=self.DEFAULT_TEMPERATURE,
                    timeout=30.0  # 30 second timeout
                )
                
                # Validate the response
                if not self._validate_api_response(response):
                    raise ValueError("Invalid API response structure")
                
                # Extract content from response
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty content received from API")
                
                # Log successful retry if this wasn't the first attempt
                if attempt > 0:
                    self.logger.info(f"API call succeeded on attempt {attempt + 1}")
                
                return content.strip()
                
            except Exception as e:
                last_exception = e
                error_message = str(e).lower()
                
                # Check if this is a rate limit error
                if "rate limit" in error_message or "quota" in error_message:
                    if attempt < max_retries:
                        delay = self._handle_rate_limit(attempt)
                        self.logger.warning(f"Rate limit hit, waiting {delay:.2f} seconds before retry {attempt + 1}")
                        time.sleep(delay)
                        continue
                
                # Check if this is a retryable error
                retryable_error_types = (ConnectionError, TimeoutError, OSError)
                retryable_error_messages = [
                    "timeout", "connection", "network", "server error", 
                    "internal error", "service unavailable", "502", "503", "504"
                ]
                
                is_retryable = (
                    isinstance(e, retryable_error_types) or
                    any(error_term in error_message for error_term in retryable_error_messages)
                )
                
                if not is_retryable or attempt >= max_retries:
                    # Non-retryable error or max retries reached
                    break
                
                # Calculate exponential backoff delay
                delay = min(base_delay * (2 ** attempt), 60.0)  # Cap at 60 seconds
                
                # Add jitter to prevent thundering herd
                delay *= (0.5 + random.random() * 0.5)
                
                self.logger.warning(
                    f"API call attempt {attempt + 1} failed: {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                
                time.sleep(delay)
        
        # All retries exhausted
        self.logger.error(f"All {max_retries + 1} API call attempts failed. Last error: {last_exception}")
        raise last_exception
    
    def _handle_rate_limit(self, retry_count: int) -> float:
        """
        Calculate delay for rate limit handling.
        
        Args:
            retry_count: Current retry attempt number (0-based)
            
        Returns:
            Delay in seconds before next retry
        """
        # Get base rate limit delay from configuration
        base_delay = self.config_manager.get_float_config('RATE_LIMIT_DELAY', 60.0)
        
        # Exponential backoff for rate limits: 60s, 120s, 240s, etc.
        delay = base_delay * (2 ** retry_count)
        
        # Cap the maximum delay at 10 minutes
        delay = min(delay, 600.0)
        
        # Add some jitter to prevent synchronized retries
        jitter = random.uniform(0.8, 1.2)
        delay *= jitter
        
        return delay
    
    def _validate_api_response(self, response: Any) -> bool:
        """
        Validate API response structure before returning content.
        
        Args:
            response: The response object from OpenAI API
            
        Returns:
            True if response is valid, False otherwise
        """
        try:
            # Check if response is the expected type
            if not isinstance(response, ChatCompletion):
                self.logger.error(f"Invalid response type: {type(response)}")
                return False
            
            # Check if response has choices
            if not hasattr(response, 'choices') or not response.choices:
                self.logger.error("Response missing choices")
                return False
            
            # Check if first choice has message
            first_choice = response.choices[0]
            if not hasattr(first_choice, 'message'):
                self.logger.error("Response choice missing message")
                return False
            
            # Check if message has content
            message = first_choice.message
            if not hasattr(message, 'content'):
                self.logger.error("Response message missing content")
                return False
            
            # Check if content is not None (empty string is valid)
            if message.content is None:
                self.logger.error("Response content is None")
                return False
            
            # Check finish reason if available
            if hasattr(first_choice, 'finish_reason'):
                finish_reason = first_choice.finish_reason
                if finish_reason not in ['stop', 'length', None]:
                    self.logger.warning(f"Unexpected finish reason: {finish_reason}")
                    # Don't fail validation for unexpected finish reasons, just log
            
            # Validate usage information if available
            if hasattr(response, 'usage'):
                usage = response.usage
                if hasattr(usage, 'total_tokens') and usage.total_tokens > 4000:
                    self.logger.warning(f"High token usage: {usage.total_tokens}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating API response: {e}")
            return False
    
    def get_model_info(self) -> dict:
        """
        Get information about the current model configuration.
        
        Returns:
            Dictionary with model information
        """
        return {
            'model_name': self.MODEL_NAME,
            'max_tokens': self.DEFAULT_MAX_TOKENS,
            'temperature': self.DEFAULT_TEMPERATURE,
            'client_initialized': self.client is not None,
            'api_key_configured': self.config_manager.validate_api_key()
        }
    
    def test_connection(self) -> bool:
        """
        Test the connection to OpenAI API with a simple request.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Make a simple test request
            test_prompt = "Say 'Hello' in one word."
            response = self.generate_content(test_prompt)
            
            # Check if we got a reasonable response
            if response and len(response.strip()) > 0:
                self.logger.info("OpenAI API connection test successful")
                return True
            else:
                self.logger.error("OpenAI API connection test failed: empty response")
                return False
                
        except Exception as e:
            self.logger.error(f"OpenAI API connection test failed: {e}")
            return False