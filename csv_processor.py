"""
CSV Processor Module for B2B AI E-commerce Content Generator

This module handles bulk file operations with memory efficiency,
including CSV validation, chunked processing, and result merging.
"""

from typing import List, Callable, Optional, TYPE_CHECKING
from io import BytesIO
import pandas as pd
import logging
import uuid
from utils import ValidationResult, ProcessingProgress

if TYPE_CHECKING:
    from content_generator import ContentGenerator
    from utils import DataValidator


class CSVProcessor:
    """
    Processor for handling CSV bulk operations with memory efficiency.
    
    This class provides chunked processing for large CSV files to prevent
    memory overflow, progress tracking, and error resilience for batch operations.
    """
    
    def __init__(self, content_generator: 'ContentGenerator'):
        """
        Initialize CSV processor with content generator.
        
        Args:
            content_generator: ContentGenerator instance for processing products
        """
        self.content_generator = content_generator
        self.logger = logging.getLogger(__name__)
        self._current_operation_id = None
        self._processed_chunks = []
        
    def process_csv_file(
        self,
        file_buffer: BytesIO,
        tone: str,
        chunk_size: int = 100,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> pd.DataFrame:
        """
        Process CSV file in chunks for memory efficiency.
        
        Args:
            file_buffer: BytesIO buffer containing CSV data
            tone: Tone of voice for content generation
            chunk_size: Number of rows to process per chunk (default: 100)
            progress_callback: Optional callback for progress updates (current, total)
            
        Returns:
            DataFrame with original data plus generated content columns
            
        Raises:
            ValueError: If CSV format is invalid or file cannot be read
            Exception: If processing fails catastrophically
        """
        # Generate unique operation ID for error recovery
        self._current_operation_id = str(uuid.uuid4())
        self._processed_chunks = []
        
        try:
            # Reset buffer position to beginning
            file_buffer.seek(0)
            
            # Read CSV file with error handling
            try:
                # Try to read the entire file first to get total row count
                df_full = pd.read_csv(file_buffer, encoding='utf-8')
            except UnicodeDecodeError:
                # Try alternative encodings
                file_buffer.seek(0)
                try:
                    df_full = pd.read_csv(file_buffer, encoding='latin-1')
                except Exception:
                    file_buffer.seek(0)
                    df_full = pd.read_csv(file_buffer, encoding='cp1252')
            except Exception as e:
                raise ValueError(f"Failed to read CSV file: {str(e)}")
            
            # Validate CSV format
            validation_result = self.validate_csv_format(df_full)
            if not validation_result.is_valid:
                raise ValueError(f"Invalid CSV format: {', '.join(validation_result.errors)}")
            
            total_rows = len(df_full)
            self.logger.info(f"Processing CSV file with {total_rows} rows in chunks of {chunk_size}")
            
            # Process file in chunks for memory efficiency
            processed_chunks = []
            rows_processed = 0
            
            # Reset buffer for chunked reading
            file_buffer.seek(0)
            
            # Use pandas chunking for memory efficiency
            chunk_reader = pd.read_csv(
                file_buffer, 
                chunksize=chunk_size,
                encoding='utf-8' if 'utf-8' in str(df_full.dtypes) else 'latin-1'
            )
            
            for chunk_index, chunk in enumerate(chunk_reader):
                try:
                    # Update progress
                    rows_processed += len(chunk)
                    if progress_callback:
                        progress_callback(rows_processed, total_rows)
                    
                    self.logger.debug(f"Processing chunk {chunk_index + 1} with {len(chunk)} rows")
                    
                    # Process this chunk
                    processed_chunk = self._process_chunk(chunk, tone)
                    processed_chunks.append(processed_chunk)
                    
                    # Store chunk for error recovery
                    self._processed_chunks.append(processed_chunk)
                    
                except Exception as e:
                    # Log error but continue with next chunk for resilience
                    self.logger.error(f"Error processing chunk {chunk_index + 1}: {str(e)}")
                    
                    # Create error chunk with original data and error status
                    error_chunk = chunk.copy()
                    error_chunk['generated_title'] = ''
                    error_chunk['generated_description'] = ''
                    error_chunk['generated_hashtags'] = ''
                    error_chunk['processing_status'] = 'chunk_error'
                    error_chunk['error_message'] = f"Chunk processing failed: {str(e)}"
                    
                    processed_chunks.append(error_chunk)
                    self._processed_chunks.append(error_chunk)
            
            # Merge all processed chunks
            if not processed_chunks:
                raise ValueError("No chunks were successfully processed")
            
            result_df = self._merge_results(processed_chunks)
            
            # Log processing summary
            successful_rows = (result_df['processing_status'] == 'success').sum()
            error_rows = (result_df['processing_status'] != 'success').sum()
            
            self.logger.info(
                f"CSV processing completed: {successful_rows} successful, "
                f"{error_rows} errors out of {total_rows} total rows"
            )
            
            # Clear operation data on success
            self._current_operation_id = None
            self._processed_chunks = []
            
            return result_df
            
        except Exception as e:
            # Preserve partial results for recovery
            if self._processed_chunks:
                self.logger.warning(
                    f"Processing failed, but {len(self._processed_chunks)} chunks were completed. "
                    f"Operation ID: {self._current_operation_id}"
                )
            
            self.logger.error(f"CSV processing failed: {str(e)}")
            raise
    
    def _process_chunk(
        self,
        chunk: pd.DataFrame,
        tone: str
    ) -> pd.DataFrame:
        """
        Process a single chunk of CSV data.
        
        Args:
            chunk: DataFrame chunk to process
            tone: Tone of voice for content generation
            
        Returns:
            DataFrame with processed chunk including generated content
        """
        # Use the content generator's bulk processing capability
        # which already handles row-by-row processing with error resilience
        try:
            processed_chunk = self.content_generator.generate_bulk_content(
                chunk, 
                tone,
                progress_callback=None  # Progress is handled at chunk level
            )
            return processed_chunk
            
        except Exception as e:
            self.logger.error(f"Chunk processing failed: {str(e)}")
            
            # Create error chunk with original data
            error_chunk = chunk.copy()
            error_chunk['generated_title'] = ''
            error_chunk['generated_description'] = ''
            error_chunk['generated_hashtags'] = ''
            error_chunk['processing_status'] = 'chunk_error'
            error_chunk['error_message'] = f"Chunk processing error: {str(e)}"
            
            return error_chunk
    
    def _merge_results(self, chunks: List[pd.DataFrame]) -> pd.DataFrame:
        """
        Merge processed chunks into final result.
        
        Args:
            chunks: List of processed DataFrame chunks
            
        Returns:
            Merged DataFrame with all processed data
            
        Raises:
            ValueError: If chunks cannot be merged or are incompatible
        """
        if not chunks:
            raise ValueError("No chunks to merge")
        
        try:
            # Concatenate all chunks
            result_df = pd.concat(chunks, ignore_index=True)
            
            # Ensure consistent column order
            expected_columns = list(chunks[0].columns)
            result_df = result_df[expected_columns]
            
            # Reset index to ensure clean sequential indexing
            result_df.reset_index(drop=True, inplace=True)
            
            self.logger.debug(f"Successfully merged {len(chunks)} chunks into {len(result_df)} rows")
            
            return result_df
            
        except Exception as e:
            self.logger.error(f"Failed to merge chunks: {str(e)}")
            raise ValueError(f"Could not merge processed chunks: {str(e)}")
    
    def validate_csv_format(self, df: pd.DataFrame) -> ValidationResult:
        """
        Validate CSV file format and required columns.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            ValidationResult indicating if CSV format is valid
        """
        # Use the data validator from content generator
        if hasattr(self.content_generator, 'validator'):
            return self.content_generator.validator.validate_csv_format(df)
        
        # Fallback validation if validator not available
        errors = []
        warnings = []
        
        if not isinstance(df, pd.DataFrame):
            return ValidationResult(
                is_valid=False,
                errors=["Input must be a pandas DataFrame"]
            )
        
        # Check for required columns
        required_columns = ['product_name']
        missing_columns = []
        for col in required_columns:
            if col not in df.columns:
                missing_columns.append(col)
        
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Check if DataFrame is empty
        if df.empty:
            errors.append("CSV file is empty")
        
        # Check for data quality issues
        if 'product_name' in df.columns:
            null_count = df['product_name'].isnull().sum()
            if null_count > 0:
                warnings.append(f"{null_count} rows have missing product names")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def get_processing_progress(self) -> Optional[ProcessingProgress]:
        """
        Get current processing progress information.
        
        Returns:
            ProcessingProgress object if operation is in progress, None otherwise
        """
        if not self._current_operation_id or not self._processed_chunks:
            return None
        
        # Calculate progress based on processed chunks
        total_chunks = len(self._processed_chunks)  # This is approximate
        current_chunks = len([chunk for chunk in self._processed_chunks if chunk is not None])
        
        return ProcessingProgress(
            current=current_chunks,
            total=total_chunks,
            status="processing",
            errors=[]
        )
    
    def recover_partial_results(self, operation_id: str) -> Optional[pd.DataFrame]:
        """
        Recover partial results from a failed operation.
        
        Args:
            operation_id: ID of the operation to recover
            
        Returns:
            DataFrame with partial results if available, None otherwise
        """
        if operation_id != self._current_operation_id or not self._processed_chunks:
            return None
        
        try:
            # Merge available chunks
            partial_result = self._merge_results(self._processed_chunks)
            self.logger.info(f"Recovered {len(partial_result)} rows from partial results")
            return partial_result
            
        except Exception as e:
            self.logger.error(f"Failed to recover partial results: {str(e)}")
            return None
    
    def clear_operation_state(self) -> None:
        """Clear current operation state and partial results."""
        self._current_operation_id = None
        self._processed_chunks = []
        self.logger.debug("Cleared CSV processor operation state")
    
    def get_chunk_size_recommendation(self, total_rows: int, available_memory_mb: int = 1024) -> int:
        """
        Get recommended chunk size based on file size and available memory.
        
        Args:
            total_rows: Total number of rows in the CSV
            available_memory_mb: Available memory in MB (default: 1024)
            
        Returns:
            Recommended chunk size
        """
        # Estimate memory usage per row (rough estimate: 1KB per row)
        estimated_row_size_kb = 1
        max_rows_in_memory = (available_memory_mb * 1024) // estimated_row_size_kb
        
        # Use conservative chunk size (25% of max capacity)
        recommended_chunk_size = max(10, min(1000, max_rows_in_memory // 4))
        
        # Adjust based on total file size
        if total_rows < 100:
            recommended_chunk_size = total_rows
        elif total_rows < 1000:
            recommended_chunk_size = min(100, recommended_chunk_size)
        
        self.logger.debug(
            f"Recommended chunk size: {recommended_chunk_size} for {total_rows} rows "
            f"with {available_memory_mb}MB available memory"
        )
        
        return recommended_chunk_size