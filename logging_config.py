"""
Logging Configuration for B2B AI E-commerce Content Generator

This module provides comprehensive logging configuration with different
levels for development, production, and testing environments.
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'operation_id'):
            log_entry['operation_id'] = record.operation_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        return json.dumps(log_entry)


class ApplicationLogger:
    """Centralized logging configuration manager."""
    
    def __init__(self, app_name: str = "b2b_ai_content_generator"):
        """Initialize application logger."""
        self.app_name = app_name
        self.log_dir = "logs"
        self.configured = False
        
        # Create logs directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
    
    def configure_logging(
        self,
        environment: str = "development",
        log_level: str = "INFO",
        enable_file_logging: bool = True,
        enable_json_logging: bool = False,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> None:
        """
        Configure application logging based on environment.
        
        Args:
            environment: Environment name (development, production, test)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_file_logging: Whether to enable file logging
            enable_json_logging: Whether to use JSON formatting (for production)
            max_file_size: Maximum size of log files before rotation
            backup_count: Number of backup log files to keep
        """
        if self.configured:
            return
        
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Set log level
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        root_logger.setLevel(numeric_level)
        
        # Configure formatters
        if enable_json_logging:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)
        
        # File handlers
        if enable_file_logging:
            # Main application log
            app_log_file = os.path.join(self.log_dir, f"{self.app_name}.log")
            file_handler = logging.handlers.RotatingFileHandler(
                app_log_file,
                maxBytes=max_file_size,
                backupCount=backup_count
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(numeric_level)
            root_logger.addHandler(file_handler)
            
            # Error log (only errors and critical)
            error_log_file = os.path.join(self.log_dir, f"{self.app_name}_errors.log")
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=max_file_size,
                backupCount=backup_count
            )
            error_handler.setFormatter(formatter)
            error_handler.setLevel(logging.ERROR)
            root_logger.addHandler(error_handler)
            
            # Performance log (for monitoring)
            if environment == "production":
                perf_log_file = os.path.join(self.log_dir, f"{self.app_name}_performance.log")
                perf_handler = logging.handlers.RotatingFileHandler(
                    perf_log_file,
                    maxBytes=max_file_size,
                    backupCount=backup_count
                )
                perf_handler.setFormatter(formatter)
                perf_handler.setLevel(logging.INFO)
                
                # Create performance logger
                perf_logger = logging.getLogger('performance')
                perf_logger.addHandler(perf_handler)
                perf_logger.setLevel(logging.INFO)
        
        # Configure specific loggers
        self._configure_component_loggers(environment, numeric_level)
        
        self.configured = True
        
        # Log configuration completion
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured for {environment} environment")
        logger.info(f"Log level: {log_level}")
        logger.info(f"File logging: {enable_file_logging}")
        logger.info(f"JSON logging: {enable_json_logging}")
    
    def _configure_component_loggers(self, environment: str, log_level: int) -> None:
        """Configure logging for specific application components."""
        # Application component loggers
        component_loggers = [
            'content_generator',
            'llm_service',
            'csv_processor',
            'utils',
            'ui',
            'main'
        ]
        
        for component in component_loggers:
            logger = logging.getLogger(component)
            logger.setLevel(log_level)
        
        # Third-party library loggers
        third_party_loggers = {
            'openai': logging.WARNING,
            'urllib3': logging.WARNING,
            'requests': logging.WARNING,
            'streamlit': logging.INFO if environment == "development" else logging.WARNING,
            'pandas': logging.WARNING,
            'numpy': logging.WARNING
        }
        
        for lib_name, lib_level in third_party_loggers.items():
            logger = logging.getLogger(lib_name)
            logger.setLevel(lib_level)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance for a specific component."""
        return logging.getLogger(name)
    
    def log_performance_metric(
        self,
        operation: str,
        duration: float,
        success: bool,
        additional_data: Optional[dict] = None
    ) -> None:
        """Log performance metrics for monitoring."""
        perf_logger = logging.getLogger('performance')
        
        metric_data = {
            'operation': operation,
            'duration_seconds': duration,
            'success': success,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if additional_data:
            metric_data.update(additional_data)
        
        perf_logger.info(f"PERFORMANCE_METRIC: {json.dumps(metric_data)}")
    
    def log_user_action(
        self,
        action: str,
        user_id: Optional[str] = None,
        additional_data: Optional[dict] = None
    ) -> None:
        """Log user actions for analytics and monitoring."""
        action_logger = logging.getLogger('user_actions')
        
        action_data = {
            'action': action,
            'user_id': user_id or 'anonymous',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if additional_data:
            action_data.update(additional_data)
        
        action_logger.info(f"USER_ACTION: {json.dumps(action_data)}")
    
    def log_api_call(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration: float,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None
    ) -> None:
        """Log API calls for monitoring and debugging."""
        api_logger = logging.getLogger('api_calls')
        
        api_data = {
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'duration_seconds': duration,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if request_size is not None:
            api_data['request_size_bytes'] = request_size
        if response_size is not None:
            api_data['response_size_bytes'] = response_size
        
        api_logger.info(f"API_CALL: {json.dumps(api_data)}")
    
    def create_operation_logger(self, operation_id: str) -> logging.LoggerAdapter:
        """Create a logger adapter with operation context."""
        logger = logging.getLogger('operations')
        return logging.LoggerAdapter(logger, {'operation_id': operation_id})


# Global logger instance
app_logger = ApplicationLogger()


def setup_logging(environment: str = "development") -> ApplicationLogger:
    """
    Setup logging for the application.
    
    Args:
        environment: Environment name (development, production, test)
        
    Returns:
        Configured ApplicationLogger instance
    """
    # Determine configuration based on environment
    if environment == "production":
        app_logger.configure_logging(
            environment=environment,
            log_level="INFO",
            enable_file_logging=True,
            enable_json_logging=True,
            max_file_size=50 * 1024 * 1024,  # 50MB for production
            backup_count=10
        )
    elif environment == "test":
        app_logger.configure_logging(
            environment=environment,
            log_level="WARNING",
            enable_file_logging=False,
            enable_json_logging=False
        )
    else:  # development
        app_logger.configure_logging(
            environment=environment,
            log_level="DEBUG",
            enable_file_logging=True,
            enable_json_logging=False,
            max_file_size=10 * 1024 * 1024,  # 10MB for development
            backup_count=3
        )
    
    return app_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a component."""
    return app_logger.get_logger(name)


# Performance monitoring decorator
def log_performance(operation_name: str):
    """Decorator to log performance metrics for functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            success = False
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                # Log the exception
                logger = get_logger(func.__module__)
                logger.error(f"Operation {operation_name} failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                app_logger.log_performance_metric(
                    operation=operation_name,
                    duration=duration,
                    success=success,
                    additional_data={
                        'function': func.__name__,
                        'module': func.__module__
                    }
                )
        
        return wrapper
    return decorator