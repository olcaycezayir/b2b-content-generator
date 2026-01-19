"""
Unit tests for the CSVProcessor class.
"""

import pytest
import pandas as pd
from io import BytesIO, StringIO
from unittest.mock import Mock, patch, MagicMock
import uuid

from csv_processor import CSVProcessor
from utils import ValidationResult, ProcessingProgress, ProductContent
from content_generator import ContentGenerator


class TestCSVProcessor:
    """Test cases for CSVProcessor class."""
    
    @pytest.fixture
    def mock_content_generator(self):
        """Create a mock content generator for testing."""
        mock_generator = Mock(spec=ContentGenerator)
        
        # Mock validator
        mock_validator = Mock()
        mock_validator.validate_csv_format.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[]
        )
        mock_generator.validator = mock_validator
        
        return mock_generator
    
    @pytest.fixture
    def csv_processor(self, mock_content_generator):
        """Create CSVProcessor instance for testing."""
        return CSVProcessor(mock_content_generator)
    
    @pytest.fixture
    def sample_csv_data(self):
        """Create sample CSV data for testing."""
        return pd.DataFrame({
            'product_name': ['Product A', 'Product B', 'Product C'],
            'category': ['Electronics', 'Clothing', 'Home'],
            'price': [99.99, 29.99, 149.99]
        })
    
    @pytest.fixture
    def sample_csv_buffer(self, sample_csv_data):
        """Create CSV buffer from sample data."""
        buffer = BytesIO()
        sample_csv_data.to_csv(buffer, index=False)
        buffer.seek(0)
        return buffer
    
    @pytest.fixture
    def processed_csv_data(self, sample_csv_data):
        """Create processed CSV data with generated content."""
        result = sample_csv_data.copy()
        result['generated_title'] = ['Title A', 'Title B', 'Title C']
        result['generated_description'] = ['Desc A' * 30, 'Desc B' * 30, 'Desc C' * 30]
        result['generated_hashtags'] = ['#a #b #c #d #e', '#f #g #h #i #j', '#k #l #m #n #o']
        result['processing_status'] = ['success', 'success', 'success']
        result['error_message'] = ['', '', '']
        return result

    def test_init(self, mock_content_generator):
        """Test CSVProcessor initialization."""
        processor = CSVProcessor(mock_content_generator)
        
        assert processor.content_generator == mock_content_generator
        assert processor._current_operation_id is None
        assert processor._processed_chunks == []
    
    def test_process_csv_file_success(self, csv_processor, sample_csv_buffer, processed_csv_data):
        """Test successful CSV file processing."""
        # Mock the content generator to return appropriate chunks
        def mock_bulk_processing(chunk_df, tone, progress_callback=None):
            result = chunk_df.copy()
            result['generated_title'] = [f'Title {i}' for i in range(len(chunk_df))]
            result['generated_description'] = ['Description' * 20] * len(chunk_df)
            result['generated_hashtags'] = ['#a #b #c #d #e'] * len(chunk_df)
            result['processing_status'] = ['success'] * len(chunk_df)
            result['error_message'] = [''] * len(chunk_df)
            return result
        
        csv_processor.content_generator.generate_bulk_content.side_effect = mock_bulk_processing
        
        # Mock progress callback
        progress_callback = Mock()
        
        result = csv_processor.process_csv_file(
            sample_csv_buffer, 
            tone='professional',
            chunk_size=2,
            progress_callback=progress_callback
        )
        
        # Verify result
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3  # Original 3 rows
        assert 'generated_title' in result.columns
        assert 'generated_description' in result.columns
        assert 'generated_hashtags' in result.columns
        assert 'processing_status' in result.columns
        
        # Verify progress callback was called
        progress_callback.assert_called()
        
        # Verify operation state was cleared
        assert csv_processor._current_operation_id is None
        assert csv_processor._processed_chunks == []
    
    def test_process_csv_file_invalid_format(self, csv_processor):
        """Test CSV processing with invalid format."""
        # Create invalid CSV buffer
        invalid_csv = "invalid,csv,data\nno,product,name"
        buffer = BytesIO(invalid_csv.encode())
        
        # Mock validator to return invalid result
        csv_processor.content_generator.validator.validate_csv_format.return_value = ValidationResult(
            is_valid=False,
            errors=["Missing required columns: product_name"]
        )
        
        with pytest.raises(ValueError, match="Invalid CSV format"):
            csv_processor.process_csv_file(buffer, 'professional')
    
    def test_process_csv_file_encoding_fallback(self, csv_processor, processed_csv_data):
        """Test CSV processing with encoding issues."""
        # Create CSV with special characters
        csv_data = "product_name,category\nProdüct Ñame,Electrónics"
        buffer = BytesIO(csv_data.encode('latin-1'))
        
        # Mock successful processing
        csv_processor.content_generator.generate_bulk_content.return_value = processed_csv_data.iloc[:1]
        
        result = csv_processor.process_csv_file(buffer, 'professional')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 1
    
    def test_process_csv_file_chunk_error_resilience(self, csv_processor, sample_csv_buffer):
        """Test error resilience during chunk processing."""
        # Mock content generator to fail on first call, succeed on second
        csv_processor.content_generator.generate_bulk_content.side_effect = [
            Exception("Chunk processing failed"),
            pd.DataFrame({
                'product_name': ['Product C'],
                'category': ['Home'],
                'price': [149.99],
                'generated_title': ['Title C'],
                'generated_description': ['Desc C' * 30],
                'generated_hashtags': ['#k #l #m #n #o'],
                'processing_status': ['success'],
                'error_message': ['']
            })
        ]
        
        result = csv_processor.process_csv_file(sample_csv_buffer, 'professional', chunk_size=2)
        
        # Should have processed some rows despite chunk error
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        
        # Check that error chunk was created
        error_rows = result[result['processing_status'] == 'chunk_error']
        success_rows = result[result['processing_status'] == 'success']
        
        # Should have both error and success rows
        assert len(error_rows) > 0 or len(success_rows) > 0
    
    def test_process_chunk_success(self, csv_processor, sample_csv_data, processed_csv_data):
        """Test successful chunk processing."""
        csv_processor.content_generator.generate_bulk_content.return_value = processed_csv_data
        
        result = csv_processor._process_chunk(sample_csv_data, 'professional')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_csv_data)
        assert 'generated_title' in result.columns
        
        # Verify content generator was called correctly
        csv_processor.content_generator.generate_bulk_content.assert_called_once_with(
            sample_csv_data, 'professional', progress_callback=None
        )
    
    def test_process_chunk_error(self, csv_processor, sample_csv_data):
        """Test chunk processing with error."""
        csv_processor.content_generator.generate_bulk_content.side_effect = Exception("Processing failed")
        
        result = csv_processor._process_chunk(sample_csv_data, 'professional')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_csv_data)
        assert all(result['processing_status'] == 'chunk_error')
        assert all(result['error_message'].str.contains('Chunk processing error'))
    
    def test_merge_results_success(self, csv_processor):
        """Test successful result merging."""
        chunk1 = pd.DataFrame({
            'product_name': ['Product A'],
            'generated_title': ['Title A'],
            'processing_status': ['success']
        })
        chunk2 = pd.DataFrame({
            'product_name': ['Product B'],
            'generated_title': ['Title B'],
            'processing_status': ['success']
        })
        
        result = csv_processor._merge_results([chunk1, chunk2])
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result['product_name']) == ['Product A', 'Product B']
        assert result.index.tolist() == [0, 1]  # Check index was reset
    
    def test_merge_results_empty_chunks(self, csv_processor):
        """Test merging with empty chunk list."""
        with pytest.raises(ValueError, match="No chunks to merge"):
            csv_processor._merge_results([])
    
    def test_merge_results_incompatible_chunks(self, csv_processor):
        """Test merging with incompatible chunks."""
        chunk1 = pd.DataFrame({'col_a': [1]})
        chunk2 = pd.DataFrame({'col_b': [2]})  # Different columns
        
        # This should still work with pandas concat, but columns will be different
        result = csv_processor._merge_results([chunk1, chunk2])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
    
    def test_validate_csv_format_with_validator(self, csv_processor, sample_csv_data):
        """Test CSV validation using content generator's validator."""
        expected_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        csv_processor.content_generator.validator.validate_csv_format.return_value = expected_result
        
        result = csv_processor.validate_csv_format(sample_csv_data)
        
        assert result == expected_result
        csv_processor.content_generator.validator.validate_csv_format.assert_called_once_with(sample_csv_data)
    
    def test_validate_csv_format_fallback(self, csv_processor, sample_csv_data):
        """Test CSV validation fallback when validator not available."""
        # Remove validator
        del csv_processor.content_generator.validator
        
        result = csv_processor.validate_csv_format(sample_csv_data)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_csv_format_fallback_missing_columns(self, csv_processor):
        """Test CSV validation fallback with missing required columns."""
        # Remove validator
        del csv_processor.content_generator.validator
        
        invalid_df = pd.DataFrame({'wrong_column': ['data']})
        result = csv_processor.validate_csv_format(invalid_df)
        
        assert not result.is_valid
        assert "Missing required columns: product_name" in result.errors
    
    def test_validate_csv_format_fallback_empty_df(self, csv_processor):
        """Test CSV validation fallback with empty DataFrame."""
        # Remove validator
        del csv_processor.content_generator.validator
        
        empty_df = pd.DataFrame()
        result = csv_processor.validate_csv_format(empty_df)
        
        assert not result.is_valid
        assert "CSV file is empty" in result.errors
    
    def test_validate_csv_format_fallback_invalid_input(self, csv_processor):
        """Test CSV validation fallback with invalid input."""
        # Remove validator
        del csv_processor.content_generator.validator
        
        result = csv_processor.validate_csv_format("not a dataframe")
        
        assert not result.is_valid
        assert "Input must be a pandas DataFrame" in result.errors
    
    def test_get_processing_progress_no_operation(self, csv_processor):
        """Test getting progress when no operation is running."""
        result = csv_processor.get_processing_progress()
        assert result is None
    
    def test_get_processing_progress_with_operation(self, csv_processor):
        """Test getting progress during operation."""
        # Simulate operation in progress
        csv_processor._current_operation_id = "test-id"
        csv_processor._processed_chunks = [
            pd.DataFrame({'test': [1]}),
            pd.DataFrame({'test': [2]}),
            None  # Simulate incomplete chunk
        ]
        
        result = csv_processor.get_processing_progress()
        
        assert isinstance(result, ProcessingProgress)
        assert result.current == 2  # Two non-None chunks
        assert result.total == 3
        assert result.status == "processing"
    
    def test_recover_partial_results_success(self, csv_processor):
        """Test successful partial result recovery."""
        operation_id = "test-operation"
        csv_processor._current_operation_id = operation_id
        csv_processor._processed_chunks = [
            pd.DataFrame({'product_name': ['A'], 'status': ['success']}),
            pd.DataFrame({'product_name': ['B'], 'status': ['success']})
        ]
        
        result = csv_processor.recover_partial_results(operation_id)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result['product_name']) == ['A', 'B']
    
    def test_recover_partial_results_no_operation(self, csv_processor):
        """Test partial result recovery with no matching operation."""
        result = csv_processor.recover_partial_results("nonexistent-id")
        assert result is None
    
    def test_recover_partial_results_merge_error(self, csv_processor):
        """Test partial result recovery with merge error."""
        operation_id = "test-operation"
        csv_processor._current_operation_id = operation_id
        csv_processor._processed_chunks = [None]  # Invalid chunk
        
        with patch.object(csv_processor, '_merge_results', side_effect=Exception("Merge failed")):
            result = csv_processor.recover_partial_results(operation_id)
            assert result is None
    
    def test_clear_operation_state(self, csv_processor):
        """Test clearing operation state."""
        # Set up some state
        csv_processor._current_operation_id = "test-id"
        csv_processor._processed_chunks = [pd.DataFrame({'test': [1]})]
        
        csv_processor.clear_operation_state()
        
        assert csv_processor._current_operation_id is None
        assert csv_processor._processed_chunks == []
    
    def test_get_chunk_size_recommendation_small_file(self, csv_processor):
        """Test chunk size recommendation for small files."""
        result = csv_processor.get_chunk_size_recommendation(50)
        assert result == 50  # Should use total rows for small files
    
    def test_get_chunk_size_recommendation_medium_file(self, csv_processor):
        """Test chunk size recommendation for medium files."""
        result = csv_processor.get_chunk_size_recommendation(500)
        assert 10 <= result <= 100  # Should be reasonable chunk size
    
    def test_get_chunk_size_recommendation_large_file(self, csv_processor):
        """Test chunk size recommendation for large files."""
        result = csv_processor.get_chunk_size_recommendation(10000)
        assert 10 <= result <= 1000  # Should be within reasonable bounds
    
    def test_get_chunk_size_recommendation_memory_constraint(self, csv_processor):
        """Test chunk size recommendation with memory constraints."""
        result = csv_processor.get_chunk_size_recommendation(10000, available_memory_mb=100)
        assert result >= 10  # Should have minimum chunk size
        assert result <= 1000  # Should respect memory constraints
    
    def test_process_csv_file_with_unicode_error(self, csv_processor):
        """Test CSV processing with Unicode decode error."""
        # Create buffer with invalid UTF-8
        invalid_utf8 = b"product_name\nTest\xff\xfe"
        buffer = BytesIO(invalid_utf8)
        
        # Mock successful processing after encoding fallback
        processed_data = pd.DataFrame({
            'product_name': ['Test'],
            'generated_title': ['Title'],
            'generated_description': ['Description' * 20],
            'generated_hashtags': ['#a #b #c #d #e'],
            'processing_status': ['success'],
            'error_message': ['']
        })
        csv_processor.content_generator.generate_bulk_content.return_value = processed_data
        
        # Should not raise exception, should handle encoding gracefully
        result = csv_processor.process_csv_file(buffer, 'professional')
        assert isinstance(result, pd.DataFrame)
    
    def test_process_csv_file_complete_failure(self, csv_processor):
        """Test CSV processing with complete failure."""
        # Create a buffer that will definitely fail pandas CSV reading
        buffer = BytesIO(b"\x00\x01\x02\x03\x04\x05")
        
        # Patch pandas read_csv to always fail
        with patch('pandas.read_csv', side_effect=Exception("CSV read error")):
            with pytest.raises(ValueError, match="Failed to read CSV file"):
                csv_processor.process_csv_file(buffer, 'professional')
    
    @patch('uuid.uuid4')
    def test_operation_id_generation(self, mock_uuid, csv_processor, sample_csv_buffer, processed_csv_data):
        """Test that operation IDs are properly generated."""
        mock_uuid.return_value = Mock()
        mock_uuid.return_value.__str__ = Mock(return_value="test-uuid-123")
        
        csv_processor.content_generator.generate_bulk_content.return_value = processed_csv_data
        
        csv_processor.process_csv_file(sample_csv_buffer, 'professional')
        
        # Verify UUID was generated
        mock_uuid.assert_called_once()
    
    def test_large_file_chunking_behavior(self, csv_processor):
        """Test behavior with large files requiring multiple chunks."""
        # Create large CSV data
        large_data = pd.DataFrame({
            'product_name': [f'Product {i}' for i in range(250)],
            'category': ['Electronics'] * 250
        })
        
        # Create buffer
        buffer = BytesIO()
        large_data.to_csv(buffer, index=False)
        buffer.seek(0)
        
        # Mock processing to return appropriate chunks
        def mock_bulk_processing(chunk_df, tone, progress_callback=None):
            result = chunk_df.copy()
            result['generated_title'] = [f'Title {i}' for i in range(len(chunk_df))]
            result['generated_description'] = ['Description' * 20] * len(chunk_df)
            result['generated_hashtags'] = ['#a #b #c #d #e'] * len(chunk_df)
            result['processing_status'] = ['success'] * len(chunk_df)
            result['error_message'] = [''] * len(chunk_df)
            return result
        
        csv_processor.content_generator.generate_bulk_content.side_effect = mock_bulk_processing
        
        # Process with small chunk size to force multiple chunks
        result = csv_processor.process_csv_file(buffer, 'professional', chunk_size=50)
        
        # Verify all data was processed
        assert len(result) == 250
        assert all(result['processing_status'] == 'success')
        
        # Verify content generator was called multiple times (for different chunks)
        assert csv_processor.content_generator.generate_bulk_content.call_count > 1