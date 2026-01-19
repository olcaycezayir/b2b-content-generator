"""
Streamlit UI Interface for B2B AI E-commerce Content Generator

This module provides the user interface components for both single product
and bulk processing modes of the content generator application.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from io import BytesIO
import pandas as pd
import logging
import time
from utils import ConfigurationManager, ErrorHandler, ValidationResult


class UISessionManager:
    """Manages session state for data preservation across UI interactions."""
    
    @staticmethod
    def initialize_session_state():
        """Initialize session state variables if they don't exist."""
        # Mode selection state
        if 'selected_mode' not in st.session_state:
            st.session_state.selected_mode = "Single Product"
        
        # Single product mode state
        if 'single_product_name' not in st.session_state:
            st.session_state.single_product_name = ""
        if 'single_tone' not in st.session_state:
            st.session_state.single_tone = "professional"
        if 'single_generated_content' not in st.session_state:
            st.session_state.single_generated_content = None
        if 'single_image_data' not in st.session_state:
            st.session_state.single_image_data = None
        
        # Bulk processing mode state
        if 'bulk_uploaded_file' not in st.session_state:
            st.session_state.bulk_uploaded_file = None
        if 'bulk_tone' not in st.session_state:
            st.session_state.bulk_tone = "professional"
        if 'bulk_processed_data' not in st.session_state:
            st.session_state.bulk_processed_data = None
        if 'bulk_processing_progress' not in st.session_state:
            st.session_state.bulk_processing_progress = None
        
        # Error handling state
        if 'error_messages' not in st.session_state:
            st.session_state.error_messages = []
        if 'success_messages' not in st.session_state:
            st.session_state.success_messages = []
        if 'warning_messages' not in st.session_state:
            st.session_state.warning_messages = []
    
    @staticmethod
    def clear_messages():
        """Clear all message states."""
        st.session_state.error_messages = []
        st.session_state.success_messages = []
        st.session_state.warning_messages = []
    
    @staticmethod
    def add_error_message(message: str):
        """Add an error message to session state."""
        if 'error_messages' not in st.session_state:
            st.session_state.error_messages = []
        st.session_state.error_messages.append(message)
    
    @staticmethod
    def add_success_message(message: str):
        """Add a success message to session state."""
        if 'success_messages' not in st.session_state:
            st.session_state.success_messages = []
        st.session_state.success_messages.append(message)
    
    @staticmethod
    def add_warning_message(message: str):
        """Add a warning message to session state."""
        if 'warning_messages' not in st.session_state:
            st.session_state.warning_messages = []
        st.session_state.warning_messages.append(message)


class MessageDisplay:
    """Handles user-friendly message display with proper formatting."""
    
    @staticmethod
    def display_messages():
        """Display all messages from session state with appropriate styling."""
        # Display error messages
        if st.session_state.get('error_messages'):
            for error_msg in st.session_state.error_messages:
                st.error(error_msg)
        
        # Display success messages
        if st.session_state.get('success_messages'):
            for success_msg in st.session_state.success_messages:
                st.success(success_msg)
        
        # Display warning messages
        if st.session_state.get('warning_messages'):
            for warning_msg in st.session_state.warning_messages:
                st.warning(warning_msg)
    
    @staticmethod
    def display_validation_result(validation_result: ValidationResult, context: str = ""):
        """Display validation results with proper formatting."""
        if not validation_result.is_valid:
            error_msg = f"**Validation Failed{' - ' + context if context else ''}:**\n"
            for error in validation_result.errors:
                error_msg += f"• {error}\n"
            UISessionManager.add_error_message(error_msg)
        
        # Display warnings even if validation passed
        if validation_result.warnings:
            warning_msg = f"**Warnings{' - ' + context if context else ''}:**\n"
            for warning in validation_result.warnings:
                warning_msg += f"• {warning}\n"
            UISessionManager.add_warning_message(warning_msg)
    
    @staticmethod
    def display_configuration_status(config_manager: ConfigurationManager):
        """Display configuration status and setup instructions if needed."""
        validation_result = config_manager.validate_configuration()
        
        if not validation_result.is_valid:
            st.error("⚙️ **Configuration Issues Detected**")
            
            # Show setup instructions
            setup_instructions = config_manager.get_setup_instructions()
            st.markdown(setup_instructions)
            
            # Show detailed errors
            MessageDisplay.display_validation_result(validation_result, "Configuration")
            
            return False
        else:
            # Configuration is valid - show brief status
            if validation_result.warnings:
                MessageDisplay.display_validation_result(validation_result, "Configuration")
            
            return True


class SingleProductInterface:
    """Interface for single product content generation mode."""
    
    def __init__(self):
        """Initialize single product interface."""
        self.logger = logging.getLogger(__name__)
    
    def render_input_section(self) -> Dict[str, Any]:
        """Render the input section for single product mode."""
        st.subheader("📝 Product Information")
        
        # Create two columns for input methods
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Option 1: Text Input**")
            product_name = st.text_input(
                "Product Name",
                value=st.session_state.single_product_name,
                placeholder="Enter your product name...",
                help="Provide a descriptive name for your product"
            )
            
            # Update session state
            if product_name != st.session_state.single_product_name:
                st.session_state.single_product_name = product_name
        
        with col2:
            st.markdown("**Option 2: Image Upload**")
            uploaded_file = st.file_uploader(
                "Upload Product Image",
                type=['png', 'jpg', 'jpeg'],
                help="Upload an image of your product for AI analysis"
            )
            
            # Handle image upload
            image_data = None
            if uploaded_file is not None:
                image_data = uploaded_file.read()
                st.session_state.single_image_data = image_data
                
                # Show image preview
                st.image(image_data, caption=f"Uploaded: {uploaded_file.name}", width=200)
                st.success(f"✅ Image uploaded: {uploaded_file.name}")
                
                # Show image info
                file_size_mb = len(image_data) / (1024 * 1024)
                st.caption(f"Size: {file_size_mb:.2f} MB")
                
            elif st.session_state.single_image_data is not None:
                image_data = st.session_state.single_image_data
                st.image(image_data, caption="Previously uploaded image", width=200)
                st.info("📷 Image from previous upload is available")
                
                # Add button to clear image
                if st.button("🗑️ Clear Image", key="clear_image"):
                    st.session_state.single_image_data = None
                    st.rerun()
        
        # Show input validation
        has_text_input = bool(product_name and product_name.strip())
        has_image_input = image_data is not None
        
        if not has_text_input and not has_image_input:
            st.warning("⚠️ Please provide either a product name or upload an image to continue.")
        
        return {
            'product_name': product_name.strip() if product_name else None,
            'image_data': image_data,
            'has_valid_input': has_text_input or has_image_input
        }
    
    def render_tone_selector(self) -> str:
        """Render tone of voice selector."""
        st.subheader("🎨 Tone of Voice")
        
        # Get tone options from ContentGenerator
        try:
            from content_generator import ContentGenerator
            tone_options = ContentGenerator.TONE_PROFILES
        except ImportError:
            # Fallback tone options if import fails
            tone_options = {
                'professional': {'description': 'Professional - Formal, business-focused language'},
                'casual': {'description': 'Casual - Friendly, conversational tone'},
                'luxury': {'description': 'Luxury - Sophisticated, high-end positioning'},
                'energetic': {'description': 'Energetic - Dynamic, exciting language'},
                'minimalist': {'description': 'Minimalist - Clean, simple, direct language'}
            }
        
        # Create selectbox with descriptions
        tone_names = list(tone_options.keys())
        current_index = tone_names.index(st.session_state.single_tone) if st.session_state.single_tone in tone_names else 0
        
        selected_tone = st.selectbox(
            "Choose Content Tone",
            options=tone_names,
            index=current_index,
            format_func=lambda x: tone_options[x]['description'],
            help="Select the tone of voice for your generated content"
        )
        
        # Show detailed information about selected tone
        if selected_tone in tone_options:
            tone_profile = tone_options[selected_tone]
            
            # Create info box with tone details
            with st.expander(f"ℹ️ About {selected_tone.title()} Tone", expanded=False):
                st.markdown(f"**Style:** {tone_profile.get('style', 'Not specified')}")
                
                if 'keywords' in tone_profile:
                    keywords = tone_profile['keywords']
                    st.markdown(f"**Key characteristics:** {', '.join(keywords)}")
                
                # Show example phrases or characteristics
                tone_examples = {
                    'professional': "Uses formal language, focuses on quality and reliability, emphasizes business value",
                    'casual': "Friendly and approachable, uses conversational language, feels personal and relatable",
                    'luxury': "Sophisticated and exclusive, emphasizes premium quality, creates desire and aspiration",
                    'energetic': "Dynamic and exciting, uses action words, creates enthusiasm and urgency",
                    'minimalist': "Clean and direct, focuses on essentials, avoids unnecessary words"
                }
                
                if selected_tone in tone_examples:
                    st.markdown(f"**Example approach:** {tone_examples[selected_tone]}")
        
        # Update session state
        if selected_tone != st.session_state.single_tone:
            st.session_state.single_tone = selected_tone
        
        return selected_tone
    
    def render_results_section(self, content) -> None:
        """Render the results section with generated content."""
        if content is None:
            return
        
        st.subheader("✨ Generated Content")
        
        # Display title with edit capability
        st.markdown("**📋 SEO-Optimized Title:**")
        title_col1, title_col2 = st.columns([4, 1])
        
        with title_col1:
            # Allow editing of title
            edited_title = st.text_input(
                "Title (max 60 characters)",
                value=content.title,
                max_chars=60,
                key="edit_title",
                label_visibility="collapsed"
            )
            
            # Update content if edited
            if edited_title != content.title:
                content.title = edited_title
                st.session_state.single_generated_content = content
        
        with title_col2:
            # Character count indicator
            char_count = len(edited_title)
            color = "green" if char_count <= 60 else "red"
            st.markdown(f"<span style='color: {color}'>{char_count}/60</span>", unsafe_allow_html=True)
        
        # Display description with edit capability
        st.markdown("**📝 Product Description:**")
        edited_description = st.text_area(
            "Description (100-300 words)",
            value=content.description,
            height=150,
            key="edit_description",
            label_visibility="collapsed"
        )
        
        # Update content if edited and show word count
        if edited_description != content.description:
            content.description = edited_description
            st.session_state.single_generated_content = content
        
        # Word count indicator
        word_count = len(edited_description.split())
        if word_count < 100:
            word_color = "red"
            word_status = "Too short"
        elif word_count > 300:
            word_color = "red"
            word_status = "Too long"
        else:
            word_color = "green"
            word_status = "Perfect"
        
        st.markdown(f"<span style='color: {word_color}'>Words: {word_count} ({word_status})</span>", unsafe_allow_html=True)
        
        # Display hashtags with edit capability
        st.markdown("**🏷️ Instagram Hashtags:**")
        hashtag_col1, hashtag_col2 = st.columns([4, 1])
        
        with hashtag_col1:
            # Allow editing hashtags as a single string
            hashtag_text = " ".join(content.hashtags)
            edited_hashtags = st.text_input(
                "Hashtags (5 hashtags, space-separated)",
                value=hashtag_text,
                key="edit_hashtags",
                label_visibility="collapsed",
                help="Enter 5 hashtags separated by spaces. Each should start with #"
            )
            
            # Update content if edited
            if edited_hashtags != hashtag_text:
                # Parse hashtags from text
                new_hashtags = []
                for tag in edited_hashtags.split():
                    tag = tag.strip()
                    if tag and not tag.startswith('#'):
                        tag = '#' + tag
                    if tag:
                        new_hashtags.append(tag)
                
                content.hashtags = new_hashtags
                st.session_state.single_generated_content = content
        
        with hashtag_col2:
            # Hashtag count indicator
            hashtag_count = len(content.hashtags)
            hashtag_color = "green" if hashtag_count == 5 else "red"
            st.markdown(f"<span style='color: {hashtag_color}'>{hashtag_count}/5</span>", unsafe_allow_html=True)
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Copy to clipboard functionality
            formatted_content = f"""Title: {content.title}

Description:
{content.description}

Hashtags: {" ".join(content.hashtags)}"""
            
            # Use streamlit's built-in copy functionality
            if st.button("📋 Copy All", key="copy_single_content", help="Copy all content to clipboard"):
                # Store in session state for display
                st.session_state.copy_content = formatted_content
                UISessionManager.add_success_message("📋 Content copied! Use Ctrl+V to paste.")
        
        with col2:
            if st.button("🔄 Generate New", key="regenerate_single_content", help="Generate new content with same inputs"):
                # Clear current content to trigger regeneration
                st.session_state.single_generated_content = None
                UISessionManager.add_success_message("🔄 Generating new content...")
                st.rerun()
        
        with col3:
            # Validate current content
            validation_result = content.validate()
            if st.button("✅ Validate", key="validate_content", help="Check if content meets requirements"):
                if validation_result.is_valid:
                    UISessionManager.add_success_message("✅ Content is valid and meets all requirements!")
                else:
                    error_msg = "❌ Content validation failed:\n" + "\n".join([f"• {error}" for error in validation_result.errors])
                    UISessionManager.add_error_message(error_msg)
        
        with col4:
            # Download as text file
            download_content = f"""B2B AI E-commerce Content Generator
Generated Content

Title: {content.title}

Description:
{content.description}

Hashtags: {" ".join(content.hashtags)}

Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
Tone: {st.session_state.single_tone}

Content Statistics:
- Title length: {len(content.title)} characters
- Description word count: {len(content.description.split())} words
- Number of hashtags: {len(content.hashtags)}
"""
            st.download_button(
                "💾 Download",
                data=download_content,
                file_name=f"product_content_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                help="Download content as a text file"
            )
        
        # Show copy content if available
        if hasattr(st.session_state, 'copy_content') and st.session_state.copy_content:
            with st.expander("📋 Content to Copy", expanded=True):
                st.code(st.session_state.copy_content, language=None)
                if st.button("✅ Done", key="clear_copy_content"):
                    del st.session_state.copy_content
                    st.rerun()
        
        # Show validation status
        validation_result = content.validate()
        if not validation_result.is_valid:
            st.warning("⚠️ Content validation issues detected. Click 'Validate' for details.")
        elif validation_result.warnings:
            st.info("ℹ️ Content is valid but has some warnings. Click 'Validate' for details.")


class BulkProcessingInterface:
    """Interface for bulk processing mode."""
    
    def __init__(self):
        """Initialize bulk processing interface."""
        self.logger = logging.getLogger(__name__)
    
    def render_file_upload(self) -> Optional[BytesIO]:
        """Render CSV file upload component with validation feedback."""
        st.subheader("📁 File Upload")
        
        # File upload instructions
        with st.expander("📋 CSV File Requirements", expanded=False):
            st.markdown("""
            **Required Format:**
            - File type: CSV or TSV
            - Required column: `product_name`
            - Optional columns: `category`, `brand`, `price`, `description_hints`
            - Maximum file size: 50MB
            - Encoding: UTF-8 (recommended) or Latin-1
            
            **Example CSV structure:**
            ```
            product_name,category,brand,price
            "Wireless Bluetooth Headphones","Electronics","TechBrand","$99.99"
            "Organic Cotton T-Shirt","Clothing","EcoWear","$29.99"
            ```
            """)
        
        uploaded_file = st.file_uploader(
            "Upload CSV File",
            type=['csv', 'tsv'],
            help="Upload a CSV file with product information. Required column: 'product_name'",
            accept_multiple_files=False
        )
        
        if uploaded_file is not None:
            # Validate file size
            file_size_mb = uploaded_file.size / (1024 * 1024)
            if file_size_mb > 50:
                UISessionManager.add_error_message(f"❌ File too large: {file_size_mb:.2f}MB. Maximum allowed: 50MB")
                return None
            
            # Store file in session state
            st.session_state.bulk_uploaded_file = uploaded_file
            
            # Show file info
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            # File statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Size", f"{file_size_mb:.2f} MB")
            with col2:
                st.metric("File Type", uploaded_file.type or "CSV")
            with col3:
                # Show encoding detection status
                st.metric("Status", "✅ Ready")
            
            # Preview and validate the file
            try:
                # Read file for preview and validation
                file_buffer = BytesIO(uploaded_file.read())
                
                # Try different encodings
                df = None
                encoding_used = None
                
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        file_buffer.seek(0)
                        df = pd.read_csv(file_buffer)
                        encoding_used = encoding
                        break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        if encoding == 'cp1252':  # Last attempt
                            raise e
                
                if df is None:
                    UISessionManager.add_error_message("❌ Could not read file with any supported encoding")
                    return None
                
                # Show encoding info
                if encoding_used != 'utf-8':
                    UISessionManager.add_warning_message(f"⚠️ File read using {encoding_used} encoding. UTF-8 is recommended.")
                
                # Validate CSV structure
                validation_result = self.validate_csv_structure(df)
                
                if validation_result:
                    # Show file preview
                    st.markdown("**📊 File Preview:**")
                    
                    # Show column information
                    col_info_col1, col_info_col2 = st.columns(2)
                    with col_info_col1:
                        st.markdown("**Columns found:**")
                        for col in df.columns:
                            icon = "✅" if col == 'product_name' else "📋"
                            required_text = " (Required)" if col == 'product_name' else ""
                            st.markdown(f"{icon} `{col}`{required_text}")
                    
                    with col_info_col2:
                        st.markdown("**Data Quality:**")
                        total_rows = len(df)
                        
                        if 'product_name' in df.columns:
                            valid_names = df['product_name'].notna().sum()
                            empty_names = total_rows - valid_names
                            
                            st.metric("Valid Product Names", f"{valid_names}/{total_rows}")
                            if empty_names > 0:
                                st.warning(f"⚠️ {empty_names} rows have empty product names")
                        
                        # Check for duplicate product names
                        if 'product_name' in df.columns:
                            duplicates = df['product_name'].duplicated().sum()
                            if duplicates > 0:
                                st.warning(f"⚠️ {duplicates} duplicate product names found")
                    
                    # Show data preview
                    st.dataframe(df.head(10), use_container_width=True)
                    
                    # Show file statistics
                    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
                    with stats_col1:
                        st.metric("Total Rows", len(df))
                    with stats_col2:
                        st.metric("Columns", len(df.columns))
                    with stats_col3:
                        processing_estimate = len(df) * 2  # Rough estimate: 2 seconds per product
                        st.metric("Est. Time", f"{processing_estimate//60}m {processing_estimate%60}s")
                    with stats_col4:
                        has_required_col = 'product_name' in df.columns
                        st.metric("Ready to Process", "✅" if has_required_col else "❌")
                    
                    # Reset file pointer for actual processing
                    uploaded_file.seek(0)
                    return BytesIO(uploaded_file.read())
                else:
                    UISessionManager.add_error_message("❌ CSV validation failed. Please check the file format and required columns.")
                    return None
                
            except Exception as e:
                UISessionManager.add_error_message(f"❌ Error reading file: {str(e)}")
                self.logger.error(f"File upload error: {e}")
                return None
        
        elif st.session_state.bulk_uploaded_file is not None:
            # Show previously uploaded file info
            prev_file = st.session_state.bulk_uploaded_file
            st.info(f"📄 Previously uploaded: {prev_file.name}")
            
            # Add button to clear previous file
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🗑️ Clear File", key="clear_bulk_file"):
                    st.session_state.bulk_uploaded_file = None
                    st.session_state.bulk_processed_data = None
                    st.rerun()
            
            # Return the previously uploaded file
            try:
                prev_file.seek(0)
                return BytesIO(prev_file.read())
            except:
                # If previous file is no longer accessible, clear it
                st.session_state.bulk_uploaded_file = None
                st.warning("⚠️ Previous file is no longer accessible. Please upload again.")
                return None
        
        return None
    
    def render_progress_bar(self, current: int, total: int) -> None:
        """Render progress bar for bulk operations with detailed information."""
        if total > 0:
            progress = current / total
            
            # Main progress bar
            st.progress(progress, text=f"Processing: {current}/{total} products ({progress:.1%})")
            
            # Additional progress information
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Completed", current, delta=f"{current}/{total}")
            
            with col2:
                remaining = total - current
                st.metric("Remaining", remaining)
            
            with col3:
                # Estimate time remaining (rough estimate: 2 seconds per product)
                if current > 0:
                    avg_time_per_product = 2  # seconds
                    estimated_remaining_time = remaining * avg_time_per_product
                    
                    if estimated_remaining_time < 60:
                        time_text = f"{estimated_remaining_time}s"
                    else:
                        minutes = estimated_remaining_time // 60
                        seconds = estimated_remaining_time % 60
                        time_text = f"{minutes}m {seconds}s"
                    
                    st.metric("Est. Time Left", time_text)
                else:
                    st.metric("Est. Time Left", "Calculating...")
            
            # Show percentage as a visual indicator
            if progress >= 1.0:
                st.success("🎉 Processing completed!")
            elif progress >= 0.75:
                st.info("🔄 Almost done...")
            elif progress >= 0.5:
                st.info("🔄 Halfway there...")
            elif progress >= 0.25:
                st.info("🔄 Making good progress...")
            else:
                st.info("🔄 Getting started...")
    
    def render_download_section(self, processed_data: pd.DataFrame) -> None:
        """Render download section for processed results with detailed analysis."""
        if processed_data is None or processed_data.empty:
            return
        
        st.subheader("📥 Download Results")
        
        # Processing summary with detailed metrics
        total_rows = len(processed_data)
        successful_rows = len(processed_data[processed_data['processing_status'] == 'success'])
        error_rows = total_rows - successful_rows
        success_rate = (successful_rows / total_rows) * 100 if total_rows > 0 else 0
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Products", total_rows)
        with col2:
            st.metric("Successfully Processed", successful_rows, delta=f"{success_rate:.1f}%")
        with col3:
            st.metric("Errors", error_rows, delta=f"{(error_rows/total_rows)*100:.1f}%" if error_rows > 0 else None)
        with col4:
            # Calculate average content length for successful rows
            if successful_rows > 0:
                successful_data = processed_data[processed_data['processing_status'] == 'success']
                avg_title_length = successful_data['generated_title'].str.len().mean()
                st.metric("Avg Title Length", f"{avg_title_length:.0f} chars")
            else:
                st.metric("Avg Title Length", "N/A")
        
        # Quality indicators
        if successful_rows > 0:
            st.markdown("**📊 Content Quality Analysis:**")
            
            quality_col1, quality_col2 = st.columns(2)
            
            with quality_col1:
                # Title length analysis
                successful_data = processed_data[processed_data['processing_status'] == 'success']
                title_lengths = successful_data['generated_title'].str.len()
                
                valid_titles = (title_lengths <= 60).sum()
                long_titles = (title_lengths > 60).sum()
                
                st.markdown(f"**Titles:**")
                st.markdown(f"✅ Valid length (≤60 chars): {valid_titles}")
                if long_titles > 0:
                    st.markdown(f"⚠️ Too long (>60 chars): {long_titles}")
            
            with quality_col2:
                # Description word count analysis
                description_word_counts = successful_data['generated_description'].str.split().str.len()
                
                valid_descriptions = ((description_word_counts >= 100) & (description_word_counts <= 300)).sum()
                short_descriptions = (description_word_counts < 100).sum()
                long_descriptions = (description_word_counts > 300).sum()
                
                st.markdown(f"**Descriptions:**")
                st.markdown(f"✅ Valid length (100-300 words): {valid_descriptions}")
                if short_descriptions > 0:
                    st.markdown(f"⚠️ Too short (<100 words): {short_descriptions}")
                if long_descriptions > 0:
                    st.markdown(f"⚠️ Too long (>300 words): {long_descriptions}")
        
        # Results preview with filtering options
        st.markdown("**📊 Results Preview:**")
        
        # Filter options
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            status_filter = st.selectbox(
                "Filter by Status",
                options=["All", "Success Only", "Errors Only"],
                key="bulk_results_filter"
            )
        
        with filter_col2:
            show_columns = st.multiselect(
                "Show Columns",
                options=list(processed_data.columns),
                default=['product_name', 'generated_title', 'processing_status'],
                key="bulk_results_columns"
            )
        
        # Apply filters
        display_data = processed_data.copy()
        
        if status_filter == "Success Only":
            display_data = display_data[display_data['processing_status'] == 'success']
        elif status_filter == "Errors Only":
            display_data = display_data[display_data['processing_status'] != 'success']
        
        if show_columns:
            # Ensure processing_status is always included for context
            if 'processing_status' not in show_columns:
                show_columns.append('processing_status')
            display_data = display_data[show_columns]
        
        # Show filtered data
        st.dataframe(display_data, use_container_width=True, height=400)
        
        # Download options
        st.markdown("**💾 Download Options:**")
        
        download_col1, download_col2, download_col3 = st.columns(3)
        
        with download_col1:
            # Download complete results
            csv_data = processed_data.to_csv(index=False)
            st.download_button(
                "📄 Download All Results (CSV)",
                data=csv_data,
                file_name=f"bulk_processed_products_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                help="Download complete results including errors"
            )
        
        with download_col2:
            # Download successful results only
            if successful_rows > 0:
                successful_data = processed_data[processed_data['processing_status'] == 'success']
                success_csv = successful_data.to_csv(index=False)
                st.download_button(
                    "✅ Download Success Only (CSV)",
                    data=success_csv,
                    file_name=f"successful_products_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    help="Download only successfully processed products"
                )
            else:
                st.button(
                    "✅ Download Success Only (CSV)",
                    disabled=True,
                    use_container_width=True,
                    help="No successful results to download"
                )
        
        with download_col3:
            # Download processing report
            report_data = self._generate_processing_report(processed_data)
            st.download_button(
                "📊 Download Report (TXT)",
                data=report_data,
                file_name=f"processing_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True,
                help="Download detailed processing report"
            )
        
        # Show errors section if there are any
        if error_rows > 0:
            with st.expander(f"⚠️ View Processing Errors ({error_rows} products)", expanded=False):
                error_data = processed_data[processed_data['processing_status'] != 'success']
                
                # Group errors by type
                error_types = error_data['error_message'].value_counts()
                
                if len(error_types) > 0:
                    st.markdown("**Error Summary:**")
                    for error_msg, count in error_types.items():
                        st.markdown(f"• `{error_msg}`: {count} products")
                    
                    st.markdown("**Detailed Error List:**")
                    error_display = error_data[['product_name', 'processing_status', 'error_message']].copy()
                    st.dataframe(error_display, use_container_width=True)
                    
                    # Download errors only
                    error_csv = error_data.to_csv(index=False)
                    st.download_button(
                        "📥 Download Errors Only (CSV)",
                        data=error_csv,
                        file_name=f"processing_errors_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        help="Download only products that had processing errors"
                    )
        
        # Processing statistics
        with st.expander("📈 Detailed Statistics", expanded=False):
            if successful_rows > 0:
                successful_data = processed_data[processed_data['processing_status'] == 'success']
                
                # Title statistics
                st.markdown("**Title Analysis:**")
                title_lengths = successful_data['generated_title'].str.len()
                st.markdown(f"• Average length: {title_lengths.mean():.1f} characters")
                st.markdown(f"• Min length: {title_lengths.min()} characters")
                st.markdown(f"• Max length: {title_lengths.max()} characters")
                
                # Description statistics
                st.markdown("**Description Analysis:**")
                desc_word_counts = successful_data['generated_description'].str.split().str.len()
                st.markdown(f"• Average length: {desc_word_counts.mean():.1f} words")
                st.markdown(f"• Min length: {desc_word_counts.min()} words")
                st.markdown(f"• Max length: {desc_word_counts.max()} words")
                
                # Hashtag analysis
                st.markdown("**Hashtag Analysis:**")
                hashtag_counts = successful_data['generated_hashtags'].str.split().str.len()
                st.markdown(f"• Average count: {hashtag_counts.mean():.1f} hashtags")
                
                # Most common hashtags
                all_hashtags = []
                for hashtag_str in successful_data['generated_hashtags']:
                    if pd.notna(hashtag_str):
                        all_hashtags.extend(hashtag_str.split())
                
                if all_hashtags:
                    hashtag_freq = pd.Series(all_hashtags).value_counts().head(10)
                    st.markdown("**Most Common Hashtags:**")
                    for hashtag, count in hashtag_freq.items():
                        st.markdown(f"• {hashtag}: {count} times")
    
    def _generate_processing_report(self, processed_data: pd.DataFrame) -> str:
        """Generate a detailed processing report."""
        total_rows = len(processed_data)
        successful_rows = len(processed_data[processed_data['processing_status'] == 'success'])
        error_rows = total_rows - successful_rows
        
        report = f"""B2B AI E-commerce Content Generator - Processing Report
Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

PROCESSING SUMMARY
==================
Total Products Processed: {total_rows}
Successfully Generated: {successful_rows} ({(successful_rows/total_rows)*100:.1f}%)
Processing Errors: {error_rows} ({(error_rows/total_rows)*100:.1f}%)

"""
        
        if successful_rows > 0:
            successful_data = processed_data[processed_data['processing_status'] == 'success']
            
            # Content quality analysis
            title_lengths = successful_data['generated_title'].str.len()
            desc_word_counts = successful_data['generated_description'].str.split().str.len()
            
            report += f"""CONTENT QUALITY ANALYSIS
========================
Title Statistics:
- Average length: {title_lengths.mean():.1f} characters
- Valid titles (≤60 chars): {(title_lengths <= 60).sum()}/{successful_rows}
- Longest title: {title_lengths.max()} characters

Description Statistics:
- Average length: {desc_word_counts.mean():.1f} words
- Valid descriptions (100-300 words): {((desc_word_counts >= 100) & (desc_word_counts <= 300)).sum()}/{successful_rows}
- Longest description: {desc_word_counts.max()} words

"""
        
        if error_rows > 0:
            error_data = processed_data[processed_data['processing_status'] != 'success']
            error_types = error_data['error_message'].value_counts()
            
            report += f"""ERROR ANALYSIS
==============
"""
            for error_msg, count in error_types.items():
                report += f"- {error_msg}: {count} products\n"
            
            report += f"""
FAILED PRODUCTS
===============
"""
            for _, row in error_data.iterrows():
                report += f"- {row['product_name']}: {row['error_message']}\n"
        
        report += f"""
PROCESSING DETAILS
==================
File processed in chunks for memory efficiency
Error resilience: Processing continued despite individual product failures
All original data preserved in output file

For technical support or questions about this report,
please refer to the application documentation.
"""
        
        return report
    
    def validate_csv_structure(self, df: pd.DataFrame) -> bool:
        """Validate CSV file structure."""
        from utils import DataValidator
        
        validator = DataValidator()
        validation_result = validator.validate_csv_format(df)
        
        MessageDisplay.display_validation_result(validation_result, "CSV File")
        
        return validation_result.is_valid


def render_navigation():
    """Render the main navigation and mode selection."""
    st.sidebar.title("🛍️ Navigation")
    
    # Mode selection with session state preservation
    mode_options = ["Single Product", "Bulk Processing"]
    current_mode_index = mode_options.index(st.session_state.selected_mode) if st.session_state.selected_mode in mode_options else 0
    
    selected_mode = st.sidebar.selectbox(
        "Select Mode",
        mode_options,
        index=current_mode_index,
        help="Choose between single product generation or bulk processing"
    )
    
    # Update session state if mode changed
    if selected_mode != st.session_state.selected_mode:
        st.session_state.selected_mode = selected_mode
        # Clear messages when switching modes
        UISessionManager.clear_messages()
    
    # Add mode descriptions
    if selected_mode == "Single Product":
        st.sidebar.markdown("""
        **Single Product Mode:**
        - Generate content for one product at a time
        - Upload images or enter product names
        - Instant results with copy/download options
        """)
    else:
        st.sidebar.markdown("""
        **Bulk Processing Mode:**
        - Process multiple products from CSV files
        - Progress tracking for large batches
        - Download results as CSV
        """)
    
    # Add help section
    with st.sidebar.expander("ℹ️ Help & Tips"):
        st.markdown("""
        **Getting Started:**
        1. Configure your OpenAI API key
        2. Choose your processing mode
        3. Upload content or files
        4. Select tone of voice
        5. Generate and download results
        
        **Supported Formats:**
        - Images: PNG, JPG, JPEG
        - Files: CSV, TSV
        - Max file size: 50MB
        """)
    
    return selected_mode


def main():
    """Main Streamlit application entry point."""
    # Initialize session state
    UISessionManager.initialize_session_state()
    
    # Main header
    st.title("🛍️ B2B AI E-commerce Content Generator")
    st.markdown("**Generate SEO-optimized product content with AI**")
    st.markdown("---")
    
    # Check if services are initialized (should be done by main application)
    if 'app_services' not in st.session_state:
        st.error("❌ Application services not initialized. Please restart the application.")
        st.info("💡 Make sure to run the application using: `streamlit run main.py`")
        st.stop()
    
    # Get services from session state
    services = st.session_state.app_services
    config_manager = services['config_manager']
    
    # Display configuration status
    config_valid = MessageDisplay.display_configuration_status(config_manager)
    
    if not config_valid:
        st.stop()  # Stop execution if configuration is invalid
    
    # Render navigation
    selected_mode = render_navigation()
    
    # Display any messages
    MessageDisplay.display_messages()
    
    # Render appropriate interface based on mode
    if selected_mode == "Single Product":
        st.header("🎯 Single Product Content Generation")
        st.markdown("Generate compelling content for individual products using AI")
        
        single_interface = SingleProductInterface()
        
        # Render input section
        input_data = single_interface.render_input_section()
        
        # Render tone selector
        selected_tone = single_interface.render_tone_selector()
        
        # Generate button (implementation moved to SingleProductInterface)
        if st.button("✨ Generate Content", type="primary", disabled=not input_data['has_valid_input']):
            UISessionManager.add_success_message("🚀 Content generation started! This may take a few moments...")
            
            try:
                # Get services from session state (initialized by main application)
                if 'app_services' not in st.session_state:
                    UISessionManager.add_error_message("❌ Application services not initialized. Please restart the application.")
                    return
                
                services = st.session_state.app_services
                content_generator = services['content_generator']
                error_handler = services['error_handler']
                
                # Import ProductInput
                from utils import ProductInput
                
                # Create ProductInput from form data
                product_input = ProductInput(
                    name=input_data['product_name'],
                    image_data=input_data['image_data']
                )
                
                # Generate content with progress indicator and error handling
                with st.spinner("Generating content..."):
                    start_time = time.time()
                    try:
                        generated_content = error_handler.wrap_operation(
                            lambda: content_generator.generate_single_product_content(product_input, selected_tone),
                            "single product content generation",
                            preserve_partial=False,
                            user_friendly_errors=False  # We'll handle errors manually for better UX
                        )
                        
                        # Record performance metric
                        duration = time.time() - start_time
                        try:
                            from monitoring import record_operation_metric
                            record_operation_metric(
                                "single_product_generation",
                                duration,
                                True,
                                tone=selected_tone,
                                has_image=input_data['image_data'] is not None,
                                product_name_length=len(input_data['product_name'] or "")
                            )
                        except ImportError:
                            pass  # Monitoring not available
                        
                    except Exception as e:
                        # Record failed operation
                        duration = time.time() - start_time
                        try:
                            from monitoring import record_operation_metric
                            record_operation_metric("single_product_generation", duration, False, error=str(e))
                        except ImportError:
                            pass
                        raise
                
                # Store in session state
                st.session_state.single_generated_content = generated_content
                
                # Update metrics
                if 'app_metrics' in st.session_state:
                    st.session_state.app_metrics['requests_processed'] += 1
                    st.session_state.app_metrics['last_activity'] = pd.Timestamp.now()
                
                # Clear any previous error messages and show success
                UISessionManager.clear_messages()
                UISessionManager.add_success_message("✨ Content generated successfully!")
                
                # Rerun to display results
                st.rerun()
                
            except Exception as e:
                # Handle errors gracefully using centralized error handler
                if 'app_services' in st.session_state:
                    error_handler = st.session_state.app_services['error_handler']
                    error_message = error_handler.handle_api_error(e, "content generation")
                else:
                    error_message = f"❌ Content generation failed: {str(e)}"
                
                UISessionManager.add_error_message(error_message)
                
                # Update error metrics
                if 'app_metrics' in st.session_state:
                    st.session_state.app_metrics['errors_encountered'] += 1
                
                # Log the error for debugging
                logging.getLogger(__name__).error(f"Content generation failed: {e}")
                
                # Clear any partial results
                st.session_state.single_generated_content = None
        
        # Render results if available
        if st.session_state.single_generated_content:
            single_interface.render_results_section(st.session_state.single_generated_content)
    
    elif selected_mode == "Bulk Processing":
        st.header("📊 Bulk Processing Mode")
        st.markdown("Process multiple products efficiently from CSV files")
        
        bulk_interface = BulkProcessingInterface()
        
        # Render file upload
        uploaded_file = bulk_interface.render_file_upload()
        
        if uploaded_file:
            # Render tone selector for bulk processing
            st.subheader("🎨 Tone of Voice")
            bulk_tone = st.selectbox(
                "Choose Content Tone for All Products",
                options=['professional', 'casual', 'luxury', 'energetic', 'minimalist'],
                index=['professional', 'casual', 'luxury', 'energetic', 'minimalist'].index(st.session_state.bulk_tone),
                format_func=lambda x: x.title(),
                help="This tone will be applied to all products in the batch"
            )
            
            # Update session state
            if bulk_tone != st.session_state.bulk_tone:
                st.session_state.bulk_tone = bulk_tone
            
            # Process button (implementation moved to BulkProcessingInterface)
            if st.button("🚀 Process All Products", type="primary"):
                UISessionManager.add_success_message("📊 Bulk processing started! This may take several minutes...")
                
                try:
                    # Get services from session state (initialized by main application)
                    if 'app_services' not in st.session_state:
                        UISessionManager.add_error_message("❌ Application services not initialized. Please restart the application.")
                        return
                    
                    services = st.session_state.app_services
                    csv_processor = services['csv_processor']
                    error_handler = services['error_handler']
                    
                    # Validate CSV structure first
                    file_buffer = BytesIO(uploaded_file.read())
                    df_preview = pd.read_csv(file_buffer)
                    
                    if not bulk_interface.validate_csv_structure(df_preview):
                        UISessionManager.add_error_message("❌ CSV validation failed. Please fix the issues and try again.")
                    else:
                        # Reset file buffer for processing
                        uploaded_file.seek(0)
                        file_buffer = BytesIO(uploaded_file.read())
                        
                        # Create progress placeholder
                        progress_placeholder = st.empty()
                        status_placeholder = st.empty()
                        
                        # Progress callback function
                        def update_progress(current: int, total: int):
                            with progress_placeholder.container():
                                bulk_interface.render_progress_bar(current, total)
                            with status_placeholder.container():
                                st.info(f"Processing product {current} of {total}...")
                        
                        # Process CSV file with progress tracking and error handling
                        with st.spinner("Processing CSV file..."):
                            start_time = time.time()
                            try:
                                processed_data = error_handler.wrap_operation(
                                    lambda: csv_processor.process_csv_file(
                                        file_buffer,
                                        bulk_tone,
                                        chunk_size=50,  # Smaller chunks for better progress updates
                                        progress_callback=update_progress
                                    ),
                                    "bulk CSV processing",
                                    preserve_partial=True,
                                    user_friendly_errors=False  # We'll handle errors manually
                                )
                                
                                # Record performance metric
                                duration = time.time() - start_time
                                try:
                                    from monitoring import record_operation_metric
                                    record_operation_metric(
                                        "bulk_csv_processing",
                                        duration,
                                        processed_data is not None,
                                        tone=bulk_tone,
                                        total_products=len(df_preview),
                                        chunk_size=50
                                    )
                                except ImportError:
                                    pass  # Monitoring not available
                                
                            except Exception as e:
                                # Record failed operation
                                duration = time.time() - start_time
                                try:
                                    from monitoring import record_operation_metric
                                    record_operation_metric("bulk_csv_processing", duration, False, error=str(e))
                                except ImportError:
                                    pass
                                raise
                        
                        # Store results in session state
                        st.session_state.bulk_processed_data = processed_data
                        
                        # Update metrics
                        if 'app_metrics' in st.session_state:
                            st.session_state.app_metrics['requests_processed'] += len(processed_data) if processed_data is not None else 0
                            st.session_state.app_metrics['last_activity'] = pd.Timestamp.now()
                        
                        # Clear progress indicators
                        progress_placeholder.empty()
                        status_placeholder.empty()
                        
                        # Show completion message
                        if processed_data is not None:
                            successful_rows = (processed_data['processing_status'] == 'success').sum()
                            total_rows = len(processed_data)
                            
                            UISessionManager.clear_messages()
                            UISessionManager.add_success_message(
                                f"✅ Bulk processing completed! {successful_rows}/{total_rows} products processed successfully."
                            )
                            
                            if successful_rows < total_rows:
                                error_count = total_rows - successful_rows
                                UISessionManager.add_warning_message(
                                    f"⚠️ {error_count} products had processing errors. Check the results for details."
                                )
                        
                        # Rerun to display results
                        st.rerun()
                
                except Exception as e:
                    # Handle errors gracefully using centralized error handler
                    if 'app_services' in st.session_state:
                        error_handler = st.session_state.app_services['error_handler']
                        error_message = error_handler.handle_api_error(e, "bulk processing")
                    else:
                        error_message = f"❌ Bulk processing failed: {str(e)}"
                    
                    UISessionManager.add_error_message(error_message)
                    
                    # Update error metrics
                    if 'app_metrics' in st.session_state:
                        st.session_state.app_metrics['errors_encountered'] += 1
                    
                    # Log the error for debugging
                    logging.getLogger(__name__).error(f"Bulk processing failed: {e}")
                    
                    # Clear any partial results
                    st.session_state.bulk_processed_data = None
        
        # Render download section if results available
        if st.session_state.bulk_processed_data is not None:
            bulk_interface.render_download_section(st.session_state.bulk_processed_data)
    
    # Application metrics and monitoring (for development/debugging)
    if config_manager.is_development():
        with st.sidebar.expander("📊 App Metrics", expanded=False):
            if 'app_metrics' in st.session_state:
                metrics = st.session_state.app_metrics
                st.json(metrics)
            
            # Add monitoring dashboard link
            if st.button("🔍 Open Monitoring Dashboard"):
                st.session_state.show_monitoring = True
        
        # Show monitoring dashboard if requested
        if st.session_state.get('show_monitoring', False):
            try:
                from monitoring import get_monitor
                monitor = get_monitor()
                monitor.render_monitoring_dashboard()
                
                if st.button("❌ Close Monitoring Dashboard"):
                    st.session_state.show_monitoring = False
            except ImportError:
                st.error("Monitoring module not available")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "💡 **Tip:** Switch between modes using the sidebar. Your progress is automatically saved!"
    )


if __name__ == "__main__":
    main()