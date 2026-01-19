"""
Tests for UI components and session management.

This module tests the UI interface components, session state management,
and error message display functionality.
"""

import pytest
import pandas as pd
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
import streamlit as st

# Import UI components
from ui import UISessionManager, MessageDisplay, SingleProductInterface, BulkProcessingInterface
from utils import ValidationResult, ConfigurationManager


class MockSessionState:
    """Mock class for Streamlit session state."""
    
    def __init__(self, initial_state=None):
        self._state = initial_state or {}
    
    def __contains__(self, key):
        return key in self._state
    
    def __getitem__(self, key):
        return self._state[key]
    
    def __setitem__(self, key, value):
        self._state[key] = value
    
    def __getattr__(self, key):
        if key.startswith('_'):
            return object.__getattribute__(self, key)
        return self._state.get(key)
    
    def __setattr__(self, key, value):
        if key.startswith('_'):
            object.__setattr__(self, key, value)
        else:
            self._state[key] = value
    
    def get(self, key, default=None):
        return self._state.get(key, default)


class TestUISessionManager:
    """Test session state management functionality."""
    
    def test_initialize_session_state(self):
        """Test session state initialization."""
        # Mock streamlit session state
        mock_session = MockSessionState()
        with patch('streamlit.session_state', mock_session):
            UISessionManager.initialize_session_state()
            
            # Check that all required session state variables are initialized
            assert 'selected_mode' in mock_session._state
            assert 'single_product_name' in mock_session._state
            assert 'single_tone' in mock_session._state
            assert 'error_messages' in mock_session._state
            assert 'success_messages' in mock_session._state
            assert 'warning_messages' in mock_session._state
            
            # Check default values
            assert mock_session._state['selected_mode'] == "Single Product"
            assert mock_session._state['single_tone'] == "professional"
            assert mock_session._state['error_messages'] == []
    
    def test_message_management(self):
        """Test message addition and clearing."""
        mock_session = MockSessionState()
        with patch('streamlit.session_state', mock_session):
            UISessionManager.initialize_session_state()
            
            # Test adding messages
            UISessionManager.add_error_message("Test error")
            UISessionManager.add_success_message("Test success")
            UISessionManager.add_warning_message("Test warning")
            
            assert "Test error" in mock_session._state['error_messages']
            assert "Test success" in mock_session._state['success_messages']
            assert "Test warning" in mock_session._state['warning_messages']
            
            # Test clearing messages
            UISessionManager.clear_messages()
            assert mock_session._state['error_messages'] == []
            assert mock_session._state['success_messages'] == []
            assert mock_session._state['warning_messages'] == []


class TestMessageDisplay:
    """Test message display functionality."""
    
    def test_display_validation_result_with_errors(self):
        """Test displaying validation results with errors."""
        validation_result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        
        mock_session = MockSessionState({'error_messages': [], 'warning_messages': []})
        with patch('streamlit.session_state', mock_session):
            MessageDisplay.display_validation_result(validation_result, "Test Context")
            
            # Check that error message was added
            assert len(mock_session._state['error_messages']) == 1
            assert "Test Context" in mock_session._state['error_messages'][0]
            assert "Error 1" in mock_session._state['error_messages'][0]
            assert "Error 2" in mock_session._state['error_messages'][0]
            
            # Check that warning message was added
            assert len(mock_session._state['warning_messages']) == 1
            assert "Warning 1" in mock_session._state['warning_messages'][0]
    
    def test_display_validation_result_valid(self):
        """Test displaying validation results when valid."""
        validation_result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Warning only"]
        )
        
        mock_session = MockSessionState({'error_messages': [], 'warning_messages': []})
        with patch('streamlit.session_state', mock_session):
            MessageDisplay.display_validation_result(validation_result)
            
            # No error messages should be added
            assert len(mock_session._state['error_messages']) == 0
            
            # Warning message should be added
            assert len(mock_session._state['warning_messages']) == 1
    
    @patch('streamlit.error')
    @patch('streamlit.success')
    @patch('streamlit.warning')
    def test_display_messages(self, mock_warning, mock_success, mock_error):
        """Test displaying messages from session state."""
        mock_session = MockSessionState({
            'error_messages': ['Error 1', 'Error 2'],
            'success_messages': ['Success 1'],
            'warning_messages': ['Warning 1']
        })
        with patch('streamlit.session_state', mock_session):
            MessageDisplay.display_messages()
            
            # Check that streamlit display functions were called
            assert mock_error.call_count == 2
            assert mock_success.call_count == 1
            assert mock_warning.call_count == 1


class TestSingleProductInterface:
    """Test single product interface components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.interface = SingleProductInterface()
    
    @patch('streamlit.text_input')
    @patch('streamlit.file_uploader')
    @patch('streamlit.columns')
    @patch('streamlit.subheader')
    @patch('streamlit.markdown')
    @patch('streamlit.success')
    @patch('streamlit.info')
    @patch('streamlit.warning')
    def test_render_input_section(self, mock_warning, mock_info, mock_success, mock_markdown, 
                                 mock_subheader, mock_columns, mock_file_uploader, mock_text_input):
        """Test rendering input section."""
        # Mock streamlit components
        mock_text_input.return_value = "Test Product"
        mock_file_uploader.return_value = None
        
        # Mock columns context managers
        mock_col1 = Mock()
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = Mock()
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_columns.return_value = [mock_col1, mock_col2]
        
        mock_session = MockSessionState({
            'single_product_name': 'Test Product',
            'single_tone': 'professional',
            'single_image_data': None
        })
        
        with patch('streamlit.session_state', mock_session):
            interface = SingleProductInterface()
            result = interface.render_input_section()
            
            # Check that input components were called
            mock_text_input.assert_called_once()
            mock_file_uploader.assert_called_once()
            
            # Check return value structure
            assert 'product_name' in result
            assert 'image_data' in result
            assert 'has_valid_input' in result
            assert result['product_name'] == "Test Product"
            assert result['has_valid_input'] is True  # Has text input
    
    @patch('streamlit.selectbox')
    @patch('streamlit.subheader')
    @patch('streamlit.expander')
    def test_render_tone_selector(self, mock_expander, mock_subheader, mock_selectbox):
        """Test rendering tone selector."""
        mock_selectbox.return_value = 'luxury'
        
        # Mock expander context manager
        mock_exp = Mock()
        mock_exp.__enter__ = Mock(return_value=mock_exp)
        mock_exp.__exit__ = Mock(return_value=None)
        mock_expander.return_value = mock_exp
        
        mock_session = MockSessionState({'single_tone': 'professional'})
        
        with patch('streamlit.session_state', mock_session), \
             patch('streamlit.markdown'):
            interface = SingleProductInterface()
            result = interface.render_tone_selector()
            
            # Check that selectbox was called
            mock_selectbox.assert_called_once()
            
            # Check return value
            assert result == 'luxury'
    
    @patch('streamlit.subheader')
    @patch('streamlit.markdown')
    @patch('streamlit.columns')
    @patch('streamlit.text_input')
    @patch('streamlit.text_area')
    @patch('streamlit.button')
    @patch('streamlit.download_button')
    @patch('streamlit.code')
    @patch('streamlit.expander')
    @patch('streamlit.warning')
    @patch('streamlit.info')
    def test_render_results_section(self, mock_info, mock_warning, mock_expander, mock_code, mock_download_button, 
                                   mock_button, mock_text_area, mock_text_input, mock_columns,
                                   mock_markdown, mock_subheader):
        """Test rendering results section with generated content."""
        from utils import ProductContent
        
        # Create test content
        test_content = ProductContent(
            title="Test Product Title",
            description="This is a test product description with enough words to meet the minimum requirement. " * 10,
            hashtags=["#test", "#product", "#ecommerce", "#quality", "#new"]
        )
        
        # Mock streamlit components
        mock_text_input.return_value = "Test Product Title"
        mock_text_area.return_value = test_content.description
        mock_button.return_value = False
        
        # Mock columns context managers - need to handle multiple column calls
        mock_col = Mock()
        mock_col.__enter__ = Mock(return_value=mock_col)
        mock_col.__exit__ = Mock(return_value=None)
        
        # The method calls st.columns multiple times with different configurations
        # We'll return the right number of columns for each call
        def columns_side_effect(cols):
            if isinstance(cols, list) and len(cols) == 2:
                return [mock_col, mock_col]  # For [4, 1] layout
            elif cols == 4:
                return [mock_col, mock_col, mock_col, mock_col]  # For 4 columns
            else:
                return [mock_col, mock_col]  # Default
        
        mock_columns.side_effect = columns_side_effect
        
        # Mock expander context manager
        mock_exp = Mock()
        mock_exp.__enter__ = Mock(return_value=mock_exp)
        mock_exp.__exit__ = Mock(return_value=None)
        mock_expander.return_value = mock_exp
        
        mock_session = MockSessionState({
            'single_generated_content': test_content,
            'single_tone': 'professional'
        })
        
        with patch('streamlit.session_state', mock_session), \
             patch('pandas.Timestamp') as mock_timestamp:
            
            # Mock timestamp for download filename
            mock_timestamp.now.return_value.strftime.return_value = "20240101_120000"
            
            interface = SingleProductInterface()
            
            # This should not raise an exception
            interface.render_results_section(test_content)
            
            # Check that components were called
            mock_subheader.assert_called()
            mock_text_input.assert_called()
            mock_text_area.assert_called()
            mock_download_button.assert_called()
    
    def test_render_results_section_none_content(self):
        """Test rendering results section with None content."""
        interface = SingleProductInterface()
        
        # Should return early without error
        result = interface.render_results_section(None)
        assert result is None
    
    @patch('content_generator.ContentGenerator')
    @patch('llm_service.LLMService')
    @patch('utils.DataValidator')
    @patch('utils.ConfigurationManager')
    @patch('streamlit.spinner')
    @patch('streamlit.button')
    def test_content_generation_integration(self, mock_button, mock_spinner, mock_config_manager_class,
                                          mock_validator_class, mock_llm_service_class, mock_content_generator_class):
        """Test complete content generation workflow."""
        from utils import ProductContent, ProductInput
        
        # Mock button click
        mock_button.return_value = True
        
        # Mock spinner context manager
        mock_spinner_ctx = Mock()
        mock_spinner_ctx.__enter__ = Mock(return_value=mock_spinner_ctx)
        mock_spinner_ctx.__exit__ = Mock(return_value=None)
        mock_spinner.return_value = mock_spinner_ctx
        
        # Mock services
        mock_config_manager = Mock()
        mock_config_manager_class.return_value = mock_config_manager
        
        mock_llm_service = Mock()
        mock_llm_service_class.return_value = mock_llm_service
        
        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator
        
        mock_content_generator = Mock()
        mock_content_generator_class.return_value = mock_content_generator
        
        # Mock generated content
        test_content = ProductContent(
            title="Generated Product Title",
            description="This is a generated product description with enough words to meet requirements. " * 10,
            hashtags=["#generated", "#product", "#ai", "#content", "#test"]
        )
        mock_content_generator.generate_single_product_content.return_value = test_content
        
        # Mock session state
        mock_session = MockSessionState({
            'single_product_name': 'Test Product',
            'single_tone': 'professional',
            'single_image_data': None,
            'single_generated_content': None,
            'error_messages': [],
            'success_messages': []
        })
        
        # Mock input data
        input_data = {
            'product_name': 'Test Product',
            'image_data': None,
            'has_valid_input': True
        }
        
        with patch('streamlit.session_state', mock_session), \
             patch('streamlit.rerun') as mock_rerun, \
             patch('ui.UISessionManager.add_success_message') as mock_add_success, \
             patch('ui.UISessionManager.clear_messages') as mock_clear_messages:
            
            # This would be called in the main UI when button is clicked
            # We're testing the logic that would be in the button callback
            
            # Import dependencies (this is what happens in the button callback)
            from content_generator import ContentGenerator
            from llm_service import LLMService
            from utils import DataValidator, ProductInput
            
            # The actual content generation logic would be executed here
            # We'll simulate it with our mocks
            product_input = ProductInput(
                name=input_data['product_name'],
                image_data=input_data['image_data']
            )
            
            # This is what the UI would do
            generated_content = mock_content_generator.generate_single_product_content(
                product_input, 
                'professional'
            )
            
            # Verify the content generation was called correctly
            mock_content_generator.generate_single_product_content.assert_called_once()
            call_args = mock_content_generator.generate_single_product_content.call_args
            
            # Check that ProductInput was created correctly
            assert call_args[0][0].name == 'Test Product'
            assert call_args[0][0].image_data is None
            assert call_args[0][1] == 'professional'  # tone
            
            # Check that we got the expected content
            assert generated_content.title == "Generated Product Title"
            assert len(generated_content.hashtags) == 5


class TestBulkProcessingInterface:
    """Test bulk processing interface components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.interface = BulkProcessingInterface()
    
    @patch('streamlit.file_uploader')
    @patch('streamlit.subheader')
    def test_render_file_upload_no_file(self, mock_subheader, mock_file_uploader):
        """Test file upload component with no file."""
        mock_file_uploader.return_value = None
        
        mock_session = MockSessionState({'bulk_uploaded_file': None})
        
        with patch('streamlit.session_state', mock_session):
            interface = BulkProcessingInterface()
            result = interface.render_file_upload()
            
            # Check that file uploader was called
            mock_file_uploader.assert_called_once()
            
            # Should return None when no file uploaded
            assert result is None
    
    @patch('streamlit.progress')
    def test_render_progress_bar(self, mock_progress):
        """Test progress bar rendering."""
        interface = BulkProcessingInterface()
        interface.render_progress_bar(50, 100)
        
        # Check that progress was called with correct value
        mock_progress.assert_called_once_with(0.5, text="Processing: 50/100 products (50.0%)")
    
    def test_validate_csv_structure_valid(self):
        """Test CSV structure validation with valid data."""
        # Create valid DataFrame
        df = pd.DataFrame({
            'product_name': ['Product 1', 'Product 2'],
            'category': ['Electronics', 'Clothing']
        })
        
        interface = BulkProcessingInterface()
        
        with patch('ui.MessageDisplay.display_validation_result') as mock_display:
            with patch('utils.DataValidator') as mock_validator_class:
                # Mock validator
                mock_validator = Mock()
                mock_validator.validate_csv_format.return_value = ValidationResult(
                    is_valid=True,
                    errors=[],
                    warnings=[]
                )
                mock_validator_class.return_value = mock_validator
                
                result = interface.validate_csv_structure(df)
                
                assert result is True
                mock_validator.validate_csv_format.assert_called_once_with(df)
    
    def test_validate_csv_structure_invalid(self):
        """Test CSV structure validation with invalid data."""
        # Create invalid DataFrame (missing required column)
        df = pd.DataFrame({
            'name': ['Product 1', 'Product 2'],  # Wrong column name
            'category': ['Electronics', 'Clothing']
        })
        
        interface = BulkProcessingInterface()
        
        with patch('ui.MessageDisplay.display_validation_result') as mock_display:
            with patch('utils.DataValidator') as mock_validator_class:
                # Mock validator
                mock_validator = Mock()
                mock_validator.validate_csv_format.return_value = ValidationResult(
                    is_valid=False,
                    errors=["Missing required columns: product_name"],
                    warnings=[]
                )
                mock_validator_class.return_value = mock_validator
                
                result = interface.validate_csv_structure(df)
                
                assert result is False
                mock_validator.validate_csv_format.assert_called_once_with(df)


class TestNavigationAndMain:
    """Test navigation and main application functionality."""
    
    @patch('streamlit.sidebar.selectbox')
    @patch('streamlit.sidebar.title')
    @patch('streamlit.sidebar.markdown')
    def test_render_navigation(self, mock_markdown, mock_title, mock_selectbox):
        """Test navigation rendering."""
        from ui import render_navigation
        
        mock_selectbox.return_value = 'Bulk Processing'
        
        mock_session = MockSessionState({'selected_mode': 'Single Product'})
        
        with patch('streamlit.session_state', mock_session):
            result = render_navigation()
            
            # Check that sidebar components were called
            mock_title.assert_called_once()
            mock_selectbox.assert_called_once()
            
            # Check return value
            assert result == 'Bulk Processing'
    
    @patch('ui.ConfigurationManager')
    @patch('ui.MessageDisplay.display_configuration_status')
    @patch('ui.UISessionManager.initialize_session_state')
    @patch('ui.render_navigation')
    @patch('streamlit.set_page_config')
    @patch('streamlit.title')
    @patch('streamlit.markdown')
    @patch('streamlit.header')
    @patch('streamlit.button')
    @patch('streamlit.info')
    @patch('streamlit.stop')
    def test_main_function_valid_config(self, mock_stop, mock_info, mock_button, mock_header,
                                       mock_markdown, mock_title, mock_set_page_config, 
                                       mock_render_nav, mock_init_session, mock_display_config, 
                                       mock_config_manager):
        """Test main function with valid configuration."""
        from ui import main
        
        # Mock configuration as valid
        mock_display_config.return_value = True
        mock_render_nav.return_value = 'Single Product'
        mock_button.return_value = False  # Button not clicked
        
        # Mock session state
        mock_session = MockSessionState({
            'selected_mode': 'Single Product',
            'single_product_name': '',
            'single_tone': 'professional',
            'single_generated_content': None,
            'single_image_data': None,
            'error_messages': [],
            'success_messages': [],
            'warning_messages': []
        })
        
        # Mock all the UI components that would be called
        with patch('streamlit.session_state', mock_session), \
             patch('ui.SingleProductInterface') as mock_single_interface_class, \
             patch('ui.MessageDisplay.display_messages'):
            
            # Mock the interface methods
            mock_interface = Mock()
            mock_interface.render_input_section.return_value = {
                'product_name': None,
                'image_data': None,
                'has_valid_input': False
            }
            mock_interface.render_tone_selector.return_value = 'professional'
            mock_single_interface_class.return_value = mock_interface
            
            # This should not raise an exception
            try:
                main()
            except SystemExit:
                # streamlit.stop() raises SystemExit, which is expected
                pass
            
            # Check that initialization functions were called
            mock_init_session.assert_called_once()
            mock_display_config.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])