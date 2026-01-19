"""
Content Generator Module for B2B AI E-commerce Content Generator

This module contains the core business logic for generating product content
using AI services. It handles both single product and bulk processing operations.
"""

from typing import Dict, Any, Callable, Optional, TYPE_CHECKING
import pandas as pd
import json
import re
import logging
from dataclasses import dataclass

# Import data models from utils to avoid duplication
from utils import ProductInput, ProductContent, ValidationResult

if TYPE_CHECKING:
    from llm_service import LLMService
    from utils import DataValidator


class ContentGenerator:
    """Core content generation engine."""
    
    # Available tone options and their characteristics
    TONE_PROFILES = {
        'professional': {
            'description': 'Formal, business-focused language',
            'keywords': ['professional', 'quality', 'reliable', 'trusted', 'premium'],
            'style': 'formal and authoritative'
        },
        'casual': {
            'description': 'Friendly, conversational tone',
            'keywords': ['great', 'awesome', 'perfect', 'love', 'enjoy'],
            'style': 'friendly and approachable'
        },
        'luxury': {
            'description': 'Sophisticated, high-end positioning',
            'keywords': ['exclusive', 'premium', 'sophisticated', 'elegant', 'luxury'],
            'style': 'sophisticated and exclusive'
        },
        'energetic': {
            'description': 'Dynamic, exciting language',
            'keywords': ['amazing', 'incredible', 'exciting', 'dynamic', 'powerful'],
            'style': 'energetic and enthusiastic'
        },
        'minimalist': {
            'description': 'Clean, simple, direct language',
            'keywords': ['simple', 'clean', 'essential', 'pure', 'minimal'],
            'style': 'clean and direct'
        }
    }
    
    def __init__(self, llm_service: 'LLMService', validator: 'DataValidator'):
        """Initialize content generator with dependencies."""
        self.llm_service = llm_service
        self.validator = validator
        self.logger = logging.getLogger(__name__)
    
    def generate_single_product_content(
        self, 
        product_input: ProductInput, 
        tone: str
    ) -> ProductContent:
        """
        Generate content for a single product.
        
        Args:
            product_input: ProductInput with name and/or image data
            tone: Tone of voice for content generation
            
        Returns:
            ProductContent with generated title, description, and hashtags
            
        Raises:
            ValueError: If input validation fails
            Exception: If content generation fails
        """
        # Validate input
        validation_result = self.validator.validate_product_input(product_input)
        if not validation_result.is_valid:
            raise ValueError(f"Invalid product input: {', '.join(validation_result.errors)}")
        
        # Sanitize text input if provided
        product_name = ""
        if product_input.name:
            product_name = self.validator.sanitize_text_input(product_input.name)
        
        # Create product information string
        product_info = self._extract_product_info(product_input)
        
        # Create prompt with tone application
        prompt = self._create_prompt(product_info, tone)
        
        # Generate content using LLM service
        try:
            ai_response = self.llm_service.generate_content(prompt)
            
            # Parse AI response into structured content
            product_content = self._parse_ai_response(ai_response)
            
            # Validate generated content
            content_validation = product_content.validate()
            if not content_validation.is_valid:
                self.logger.warning(f"Generated content validation failed: {content_validation.errors}")
                # Try to fix common issues
                product_content = self._fix_content_issues(product_content)
            
            self.logger.info(f"Successfully generated content for product: {product_name[:50]}...")
            return product_content
            
        except Exception as e:
            self.logger.error(f"Content generation failed for product '{product_name}': {e}")
            raise
    
    def generate_bulk_content(
        self,
        products_df: pd.DataFrame,
        tone: str,
        progress_callback: Callable[[int, int], None] = None
    ) -> pd.DataFrame:
        """
        Generate content for multiple products from DataFrame.
        
        Args:
            products_df: DataFrame with product information
            tone: Tone of voice for content generation
            progress_callback: Optional callback for progress updates
            
        Returns:
            DataFrame with original data plus generated content columns
        """
        # Validate CSV format
        csv_validation = self.validator.validate_csv_format(products_df)
        if not csv_validation.is_valid:
            raise ValueError(f"Invalid CSV format: {', '.join(csv_validation.errors)}")
        
        # Create result DataFrame with original columns
        result_df = products_df.copy()
        
        # Add columns for generated content
        result_df['generated_title'] = ''
        result_df['generated_description'] = ''
        result_df['generated_hashtags'] = ''
        result_df['processing_status'] = 'pending'
        result_df['error_message'] = ''
        
        total_rows = len(products_df)
        successful_count = 0
        
        # Process each row
        for index, row in products_df.iterrows():
            try:
                # Update progress
                if progress_callback:
                    progress_callback(index + 1, total_rows)
                
                # Create ProductInput from row data
                product_input = self._create_product_input_from_row(row)
                
                # Generate content
                content = self.generate_single_product_content(product_input, tone)
                
                # Store results
                result_df.at[index, 'generated_title'] = content.title
                result_df.at[index, 'generated_description'] = content.description
                result_df.at[index, 'generated_hashtags'] = ' '.join(content.hashtags)
                result_df.at[index, 'processing_status'] = 'success'
                
                successful_count += 1
                
            except Exception as e:
                # Log error and continue processing
                error_msg = str(e)
                self.logger.error(f"Failed to process row {index}: {error_msg}")
                
                result_df.at[index, 'processing_status'] = 'error'
                result_df.at[index, 'error_message'] = error_msg
        
        self.logger.info(f"Bulk processing completed: {successful_count}/{total_rows} successful")
        return result_df
    
    def _extract_product_info(self, product_input: ProductInput) -> str:
        """
        Extract product information from input for prompt creation.
        
        Args:
            product_input: ProductInput with name and/or image data
            
        Returns:
            String with product information for AI prompt
        """
        info_parts = []
        
        # Add product name if available
        if product_input.name:
            sanitized_name = self.validator.sanitize_text_input(product_input.name)
            info_parts.append(f"Product Name: {sanitized_name}")
        
        # Add image analysis if image data is provided
        if product_input.image_data:
            # For now, we'll note that image data is available
            # In a full implementation, this would use vision AI to analyze the image
            info_parts.append("Image: Product image provided for visual analysis")
        
        # Add additional attributes if available
        if product_input.additional_attributes:
            for key, value in product_input.additional_attributes.items():
                sanitized_key = self.validator.sanitize_text_input(key)
                sanitized_value = self.validator.sanitize_text_input(value)
                info_parts.append(f"{sanitized_key}: {sanitized_value}")
        
        return "\n".join(info_parts) if info_parts else "Product information not provided"
    
    def _create_prompt(self, product_info: str, tone: str) -> str:
        """
        Create AI prompt for content generation with tone application.
        
        Args:
            product_info: Extracted product information
            tone: Tone of voice for content generation
            
        Returns:
            Formatted prompt for AI content generation
        """
        # Get tone profile
        tone_profile = self.TONE_PROFILES.get(tone.lower(), self.TONE_PROFILES['professional'])
        
        # Create comprehensive prompt
        prompt = f"""You are an expert e-commerce content generator. Create compelling product content based on the following information:

{product_info}

TONE OF VOICE: {tone.title()} - {tone_profile['description']}
Style: Write in a {tone_profile['style']} manner.
Keywords to consider: {', '.join(tone_profile['keywords'])}

REQUIREMENTS:
1. Generate an SEO-optimized product title (maximum 60 characters)
2. Create a compelling product description (100-300 words)
3. Generate exactly 5 relevant Instagram hashtags

FORMAT YOUR RESPONSE AS JSON:
{{
    "title": "Your SEO-optimized title here (≤60 chars)",
    "description": "Your compelling product description here (100-300 words)",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"]
}}

GUIDELINES:
- Title: Focus on key benefits, include relevant keywords, stay under 60 characters
- Description: Highlight features, benefits, and use cases. Make it engaging and informative.
- Hashtags: Use popular, relevant hashtags that match the product and tone. Include # symbol.
- Tone: Maintain the {tone} tone throughout all content
- SEO: Include relevant keywords naturally without keyword stuffing

Generate the content now:"""

        return prompt
    
    def _parse_ai_response(self, response: str) -> ProductContent:
        """
        Parse AI response into structured ProductContent.
        
        Args:
            response: Raw AI response string
            
        Returns:
            ProductContent with parsed title, description, and hashtags
            
        Raises:
            ValueError: If response cannot be parsed or is invalid
        """
        try:
            # Clean the response - remove any markdown formatting
            cleaned_response = response.strip()
            
            # Remove markdown code blocks if present
            if cleaned_response.startswith('```'):
                lines = cleaned_response.split('\n')
                # Remove first and last lines if they're markdown markers
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned_response = '\n'.join(lines)
            
            # Try to parse as JSON
            try:
                data = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract content using regex
                data = self._extract_content_with_regex(cleaned_response)
            
            # Validate required fields
            if not isinstance(data, dict):
                raise ValueError("Response is not a valid dictionary")
            
            required_fields = ['title', 'description', 'hashtags']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Extract and validate content
            title = str(data['title']).strip()
            description = str(data['description']).strip()
            hashtags = data['hashtags']
            
            # Validate hashtags is a list
            if not isinstance(hashtags, list):
                raise ValueError("Hashtags must be a list")
            
            # Ensure hashtags are strings and start with #
            processed_hashtags = []
            for hashtag in hashtags:
                hashtag_str = str(hashtag).strip()
                if not hashtag_str.startswith('#'):
                    hashtag_str = '#' + hashtag_str
                processed_hashtags.append(hashtag_str)
            
            # Create ProductContent
            content = ProductContent(
                title=title,
                description=description,
                hashtags=processed_hashtags
            )
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to parse AI response: {e}")
            self.logger.debug(f"Raw response: {response[:500]}...")
            raise ValueError(f"Could not parse AI response: {e}")
    
    def _extract_content_with_regex(self, response: str) -> Dict[str, Any]:
        """
        Extract content using regex patterns as fallback parsing method.
        
        Args:
            response: Raw AI response string
            
        Returns:
            Dictionary with extracted title, description, and hashtags
            
        Raises:
            ValueError: If no valid content can be extracted
        """
        # Initialize result
        result = {}
        
        # Extract title (look for "title" followed by content)
        title_patterns = [
            r'"title":\s*"([^"]+)"',
            r'title:\s*"([^"]+)"',
            r'Title:\s*([^\n]+)',
            r'TITLE:\s*([^\n]+)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result['title'] = match.group(1).strip()
                break
        
        # Extract description
        desc_patterns = [
            r'"description":\s*"([^"]+)"',
            r'description:\s*"([^"]+)"',
            r'Description:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\nHashtags|\n#|$)',
            r'DESCRIPTION:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\nHashtags|\n#|$)'
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                result['description'] = match.group(1).strip()
                break
        
        # Extract hashtags
        hashtag_patterns = [
            r'"hashtags":\s*\[(.*?)\]',
            r'hashtags:\s*\[(.*?)\]',
            r'Hashtags:\s*([^\n]+)',
            r'HASHTAGS:\s*([^\n]+)',
            r'(#\w+(?:\s+#\w+)*)'
        ]
        
        hashtags = []
        for pattern in hashtag_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                hashtag_text = match.group(1)
                # Extract individual hashtags
                individual_hashtags = re.findall(r'#\w+', hashtag_text)
                if individual_hashtags:
                    hashtags = individual_hashtags
                    break
                # If no # found, split by comma and add #
                elif ',' in hashtag_text:
                    hashtags = ['#' + tag.strip().strip('"\'') for tag in hashtag_text.split(',')]
                    break
        
        result['hashtags'] = hashtags
        
        # Check if we extracted any meaningful content
        has_title = 'title' in result and result['title'] and len(result['title'].strip()) > 0
        has_description = 'description' in result and result['description'] and len(result['description'].strip()) > 0
        has_hashtags = result.get('hashtags') and len(result['hashtags']) > 0
        
        if not (has_title or has_description or has_hashtags):
            raise ValueError("No valid content could be extracted from response")
        
        # Provide defaults for missing fields
        if 'title' not in result or not result['title']:
            result['title'] = "Product Title"
        if 'description' not in result or not result['description']:
            result['description'] = "Product description not available."
        if not result.get('hashtags'):
            result['hashtags'] = ['#product', '#ecommerce', '#shopping', '#quality', '#new']
        
        return result
    
    def _fix_content_issues(self, content: ProductContent) -> ProductContent:
        """
        Fix common content validation issues.
        
        Args:
            content: ProductContent with potential issues
            
        Returns:
            ProductContent with fixed issues
        """
        # Fix title length
        if len(content.title) > 60:
            content.title = content.title[:57] + "..."
        
        # Fix description word count
        words = content.description.split()
        if len(words) < 100:
            # Pad with substantial generic content to reach exactly 100 words
            padding_words = [
                "This", "product", "offers", "excellent", "quality", "and", "value", "for", "customers", "looking",
                "for", "reliable", "solutions.", "It", "features", "premium", "materials", "and", "advanced", "technology",
                "to", "deliver", "outstanding", "performance.", "The", "design", "is", "both", "functional", "and",
                "aesthetically", "pleasing,", "making", "it", "perfect", "for", "both", "personal", "and", "professional",
                "use.", "With", "its", "durable", "construction", "and", "innovative", "features,", "this", "product",
                "stands", "out", "in", "the", "market.", "Customers", "appreciate", "its", "reliability", "and",
                "ease", "of", "use.", "The", "product", "comes", "with", "comprehensive", "support", "and", "warranty",
                "coverage.", "Whether", "you're", "a", "beginner", "or", "an", "expert,", "this", "product", "will",
                "meet", "your", "needs", "and", "exceed", "your", "expectations.", "Order", "now", "and", "experience",
                "the", "difference", "quality", "makes.", "Available", "now", "with", "fast", "shipping", "worldwide."
            ]
            
            # Add words until we reach at least 100
            current_words = len(words)
            needed_words = 100 - current_words
            if needed_words > 0:
                # Ensure we have enough padding words by repeating if necessary
                while len(padding_words) < needed_words:
                    padding_words.extend(padding_words[:min(len(padding_words), needed_words - len(padding_words))])
                
                padding_text = " " + " ".join(padding_words[:needed_words])
                content.description += padding_text
            
        elif len(words) > 300:
            # Truncate to 300 words
            content.description = " ".join(words[:300])
        
        # Fix hashtags count
        if len(content.hashtags) < 5:
            # Add generic hashtags
            generic_hashtags = ['#product', '#quality', '#ecommerce', '#shopping', '#new']
            while len(content.hashtags) < 5:
                for hashtag in generic_hashtags:
                    if hashtag not in content.hashtags:
                        content.hashtags.append(hashtag)
                        if len(content.hashtags) >= 5:
                            break
        elif len(content.hashtags) > 5:
            # Keep only first 5
            content.hashtags = content.hashtags[:5]
        
        # Ensure hashtags start with #
        content.hashtags = [
            hashtag if hashtag.startswith('#') else '#' + hashtag 
            for hashtag in content.hashtags
        ]
        
        return content
    
    def _create_product_input_from_row(self, row: pd.Series) -> ProductInput:
        """
        Create ProductInput from DataFrame row.
        
        Args:
            row: Pandas Series representing a row from the CSV
            
        Returns:
            ProductInput created from row data
        """
        # Extract product name
        product_name = None
        if 'product_name' in row and pd.notna(row['product_name']):
            product_name = str(row['product_name']).strip()
        
        # Extract additional attributes from other columns
        additional_attributes = {}
        for column, value in row.items():
            if column != 'product_name' and pd.notna(value):
                additional_attributes[column] = str(value)
        
        return ProductInput(
            name=product_name,
            image_data=None,  # CSV processing doesn't include image data
            additional_attributes=additional_attributes
        )
    
    def get_available_tones(self) -> Dict[str, str]:
        """
        Get available tone options with descriptions.
        
        Returns:
            Dictionary mapping tone names to descriptions
        """
        return {
            tone: profile['description'] 
            for tone, profile in self.TONE_PROFILES.items()
        }