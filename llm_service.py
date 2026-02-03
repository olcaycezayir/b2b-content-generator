"""
LLM Service Module for B2B AI E-commerce Content Generator

This module handles all interactions with the OpenAI API, including
retry logic, rate limiting, and response validation.
"""

from typing import Any, Optional, TYPE_CHECKING
import time
import logging
import random

if TYPE_CHECKING:
    from utils import ConfigurationManager

# Import OpenAI with error handling for missing dependency
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False


SALES_MASTER_PROMPT = """You are SalesFlow, the world's most advanced e-commerce conversion expert, neuromarketing genius, and SEO strategist.

YOUR MISSION: Transform raw product information into irresistible sales copy that targets the customer's decision-making psychology and drives conversions.

CORE STRATEGIES YOU MUST APPLY:

1. **PAS Framework (Problem-Agitation-Solution):**
   - Identify the hidden problem customers experience without this product
   - Agitate the pain point to create urgency and emotional connection
   - Present the product as the heroic solution that resolves their pain

2. **Benefit-First Language (Never Just Features):**
   - Transform every feature into a compelling customer benefit
   - Example: Don't say "5000mAh battery" → Say "All-day power that eliminates midday charging anxiety"
   - Focus on outcomes, not specifications

3. **Emotional Triggers & Psychology:**
   - Tap into core human motivations: Trust, Status, Comfort, FOMO, Savings
   - Use social proof language and authority positioning
   - Create desire through scarcity and exclusivity when appropriate

4. **SEO & Conversion Optimization:**
   - Integrate keywords naturally within compelling copy
   - Structure content for both search engines and human psychology
   - Use power words that drive action and engagement

5. **Neuromarketing Principles:**
   - Appeal to the reptilian brain (survival, reproduction, dominance)
   - Use concrete, sensory language that creates mental images
   - Build trust through specificity and proof elements

WRITING RULES:
- Ban empty adjectives like "amazing, perfect, unique" without proof
- Use "you" to create personal connection and ownership
- Write with confidence and authority, not corporate speak
- Make every word earn its place - no fluff or filler
- Create curiosity gaps that compel continued reading

TONE ADAPTATION:
- Professional: Authoritative, trustworthy, results-focused
- Casual: Friendly, relatable, conversational yet persuasive
- Luxury: Sophisticated, exclusive, aspirational
- Energetic: Dynamic, exciting, action-oriented
- Minimalist: Clean, direct, elegantly simple

Remember: Your goal is conversion, not just information. Every sentence should either build desire, overcome objections, or move toward purchase."""


class LLMService:
    """Service for interacting with OpenAI's LLM API."""
    
    # GPT-4o model specification as required
    MODEL_NAME = "gpt-4o"
    
    # Default parameters for content generation
    DEFAULT_MAX_TOKENS = 1000
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_TIMEOUT = 30.0
    
    # Retry configuration
    MAX_BACKOFF_DELAY = 60.0  # Maximum delay between retries
    MAX_RATE_LIMIT_DELAY = 600.0  # Maximum rate limit delay (10 minutes)
    JITTER_RANGE = (0.5, 1.5)  # Jitter multiplier range
    RATE_LIMIT_JITTER_RANGE = (0.8, 1.2)  # Rate limit jitter range
    
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
        
        # Clamp max_retries to at least 0 to prevent empty range
        max_retries = max(0, max_retries)
        
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
                            "content": SALES_MASTER_PROMPT
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    max_tokens=self.DEFAULT_MAX_TOKENS,
                    temperature=self.DEFAULT_TEMPERATURE,
                    timeout=self.DEFAULT_TIMEOUT
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
                if ("rate limit" in error_message or "quota" in error_message or 
                    "429" in error_message or "rate_limit_exceeded" in error_message):
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
                delay = min(base_delay * (2 ** attempt), self.MAX_BACKOFF_DELAY)
                
                # Add jitter to prevent thundering herd
                jitter_min, jitter_max = self.JITTER_RANGE
                delay *= (jitter_min + random.random() * (jitter_max - jitter_min))
                
                self.logger.warning(
                    f"API call attempt {attempt + 1} failed: {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                
                time.sleep(delay)
        
        # All retries exhausted
        if last_exception is None:
            # This should never happen due to max_retries clamping, but defensive programming
            last_exception = Exception("All retry attempts failed with no recorded exception")
        
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
        
        # Cap the maximum delay at the configured limit
        delay = min(delay, self.MAX_RATE_LIMIT_DELAY)
        
        # Add some jitter to prevent synchronized retries
        jitter_min, jitter_max = self.RATE_LIMIT_JITTER_RANGE
        jitter = random.uniform(jitter_min, jitter_max)
        delay *= jitter
        
        return delay
    
    def _validate_api_response(self, response: Any) -> bool:
        """
        Validate API response structure using duck-typing.
        
        Args:
            response: The response object from OpenAI API
            
        Returns:
            True if response is valid, False otherwise
        """
        try:
            # Use duck-typing to check for expected structure
            # Check if response has choices attribute
            if not hasattr(response, 'choices'):
                self.logger.error("Response missing 'choices' attribute")
                return False
            
            # Check if choices is not empty
            if not response.choices:
                self.logger.error("Response choices is empty")
                return False
            
            # Check if we can access the first choice safely
            try:
                first_choice = response.choices[0]
            except (IndexError, TypeError) as e:
                self.logger.error(f"Cannot access first choice: {e}")
                return False
            if not hasattr(first_choice, 'message'):
                self.logger.error("Response choice missing 'message' attribute")
                return False
            
            # Check if message has content attribute
            message = first_choice.message
            if not hasattr(message, 'content'):
                self.logger.error("Response message missing 'content' attribute")
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
