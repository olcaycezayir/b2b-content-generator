#!/usr/bin/env python3
"""
Main Application Entry Point for B2B AI E-commerce Content Generator

This module serves as the main entry point for the application, wiring together
all components including UI, business logic, and services with comprehensive
error handling, logging, and monitoring.
"""

import sys
import os
import logging
import traceback
from typing import Optional
import streamlit as st
import time

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import logging configuration first
try:
    from logging_config import setup_logging, get_logger, log_performance
except ImportError as e:
    print(f"Warning: Could not import logging configuration: {e}")
    # Fallback to basic logging
    logging.basicConfig(level=logging.INFO)
    get_logger = logging.getLogger
    def log_performance(name): 
        def decorator(func): 
            return func
        return decorator

# Import application components
try:
    from ui import main as ui_main, UISessionManager, MessageDisplay
    from utils import ConfigurationManager, ErrorHandler, DataValidator
    from llm_service import LLMService
    from content_generator import ContentGenerator
    from csv_processor import CSVProcessor
except ImportError as e:
    print(f"Critical import error: {e}")
    print("Please ensure all required modules are available and dependencies are installed.")
    sys.exit(1)


class ApplicationManager:
    """
    Main application manager that coordinates all components and provides
    centralized error handling, logging, and monitoring.
    """
    
    def __init__(self):
        """Initialize the application manager."""
        self.config_manager: Optional[ConfigurationManager] = None
        self.error_handler: Optional[ErrorHandler] = None
        self.logger: Optional[logging.Logger] = None
        self.services_initialized = False
        self.app_logger = None
        
        # Initialize core components
        self._initialize_logging()
        self._initialize_configuration()
        self._initialize_error_handling()
    
    def _initialize_logging(self) -> None:
        """Initialize comprehensive logging system."""
        try:
            # Get environment from environment variable or default to development
            environment = os.getenv('APP_ENV', 'development')
            
            # Setup logging using the logging configuration module
            self.app_logger = setup_logging(environment)
            self.logger = get_logger(__name__)
            
            self.logger.info("Application logging initialized")
            self.logger.info(f"Environment: {environment}")
            
        except Exception as e:
            # Fallback to basic logging if advanced logging fails
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout),
                    logging.FileHandler('app.log', mode='a')
                ]
            )
            
            self.logger = logging.getLogger(__name__)
            self.logger.warning(f"Advanced logging setup failed, using basic logging: {e}")
            self.logger.info("Basic application logging initialized")
    
    def _initialize_configuration(self) -> None:
        """Initialize configuration management."""
        try:
            self.config_manager = ConfigurationManager()
            self.logger.info("Configuration manager initialized")
            
            # Log configuration status (without sensitive data)
            config_summary = self.config_manager.get_safe_config_summary()
            self.logger.info(f"Configuration loaded: {config_summary}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration: {e}")
            raise
    
    def _initialize_error_handling(self) -> None:
        """Initialize error handling system."""
        try:
            self.error_handler = ErrorHandler(self.config_manager)
            self.logger.info("Error handler initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize error handler: {e}")
            raise
    
    @log_performance("service_initialization")
    def initialize_services(self) -> bool:
        """
        Initialize all application services.
        
        Returns:
            True if all services initialized successfully, False otherwise
        """
        if self.services_initialized:
            return True
        
        try:
            self.logger.info("Initializing application services...")
            
            # Validate configuration before initializing services
            validation_result = self.config_manager.validate_configuration()
            if not validation_result.is_valid:
                self.logger.error(f"Configuration validation failed: {validation_result.errors}")
                return False
            
            # Initialize LLM service
            try:
                llm_service = LLMService(self.config_manager)
                self.logger.info("LLM service initialized successfully")
                
                # Test connection
                if llm_service.test_connection():
                    self.logger.info("LLM service connection test passed")
                else:
                    self.logger.warning("LLM service connection test failed")
                    
            except Exception as e:
                self.logger.error(f"Failed to initialize LLM service: {e}")
                return False
            
            # Initialize data validator
            try:
                validator = DataValidator()
                self.logger.info("Data validator initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize data validator: {e}")
                return False
            
            # Initialize content generator
            try:
                content_generator = ContentGenerator(llm_service, validator)
                self.logger.info("Content generator initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize content generator: {e}")
                return False
            
            # Initialize CSV processor
            try:
                csv_processor = CSVProcessor(content_generator)
                self.logger.info("CSV processor initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize CSV processor: {e}")
                return False
            
            # Store services in session state for UI access
            if 'app_services' not in st.session_state:
                st.session_state.app_services = {
                    'config_manager': self.config_manager,
                    'error_handler': self.error_handler,
                    'llm_service': llm_service,
                    'validator': validator,
                    'content_generator': content_generator,
                    'csv_processor': csv_processor
                }
            
            self.services_initialized = True
            self.logger.info("All application services initialized successfully")
            
            # Log performance metrics if available
            if self.app_logger:
                self.app_logger.log_user_action(
                    "application_startup",
                    additional_data={'services_count': len(st.session_state.app_services)}
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Service initialization failed: {e}")
            self.logger.debug(f"Service initialization traceback: {traceback.format_exc()}")
            return False
    
    def run_application(self) -> None:
        """
        Run the main application with comprehensive error handling.
        """
        try:
            self.logger.info("Starting B2B AI E-commerce Content Generator application")
            
            # Initialize services
            if not self.initialize_services():
                self.logger.error("Failed to initialize services, cannot start application")
                st.error("❌ Application initialization failed. Please check configuration and try again.")
                return
            
            # Add application monitoring
            self._setup_monitoring()
            
            # Run the UI application
            ui_main()
            
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        except Exception as e:
            self.logger.error(f"Unhandled application error: {e}")
            self.logger.debug(f"Application error traceback: {traceback.format_exc()}")
            
            # Display user-friendly error message
            if self.error_handler:
                error_message = self.error_handler.create_user_friendly_message(
                    e, 
                    "application startup",
                    ["Check your configuration settings", "Restart the application", "Contact support if the issue persists"]
                )
                st.error(error_message)
            else:
                st.error(f"❌ Critical application error: {str(e)}")
        
        finally:
            self.logger.info("Application shutdown")
    
    def _setup_monitoring(self) -> None:
        """Setup application monitoring and health checks."""
        try:
            # Add performance monitoring
            if 'app_metrics' not in st.session_state:
                st.session_state.app_metrics = {
                    'startup_time': st.session_state.get('app_start_time', time.time()),
                    'requests_processed': 0,
                    'errors_encountered': 0,
                    'last_activity': None,
                    'session_id': st.session_state.get('session_id', f"session_{int(time.time())}")
                }
            
            # Log system information
            self.logger.info(f"Python version: {sys.version}")
            self.logger.info(f"Working directory: {os.getcwd()}")
            self.logger.info(f"Environment: {self.config_manager.get_config_value('APP_ENV', 'development')}")
            
            # Log application metrics
            if self.app_logger:
                self.app_logger.log_performance_metric(
                    operation="application_startup",
                    duration=time.time() - st.session_state.app_metrics['startup_time'],
                    success=True,
                    additional_data={
                        'python_version': sys.version,
                        'working_directory': os.getcwd(),
                        'session_id': st.session_state.app_metrics['session_id']
                    }
                )
            
            # Setup health check endpoint (for production monitoring)
            if self.config_manager.is_production():
                self._setup_health_checks()
            
        except Exception as e:
            self.logger.warning(f"Monitoring setup failed: {e}")
    
    def _setup_health_checks(self) -> None:
        """Setup health check endpoints for production monitoring."""
        try:
            # This would typically integrate with external monitoring services
            # For now, we'll log health status
            health_status = {
                'services_initialized': self.services_initialized,
                'config_valid': self.config_manager.validate_configuration().is_valid,
                'api_connection': False,
                'timestamp': time.time()
            }
            
            # Test API connection
            if 'app_services' in st.session_state:
                llm_service = st.session_state.app_services.get('llm_service')
                if llm_service:
                    health_status['api_connection'] = llm_service.test_connection()
            
            self.logger.info(f"Health check status: {health_status}")
            
            # Log health metrics
            if self.app_logger:
                self.app_logger.log_performance_metric(
                    operation="health_check",
                    duration=0.1,  # Health checks should be fast
                    success=health_status['config_valid'] and health_status['services_initialized'],
                    additional_data=health_status
                )
            
        except Exception as e:
            self.logger.warning(f"Health check setup failed: {e}")


def setup_streamlit_config():
    """Configure Streamlit application settings."""
    # Set page configuration
    st.set_page_config(
        page_title="B2B AI E-commerce Content Generator",
        page_icon="🛍️",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/your-repo/help',
            'Report a bug': 'https://github.com/your-repo/issues',
            'About': """
            # B2B AI E-commerce Content Generator
            
            Generate SEO-optimized product content using AI technology.
            
            **Features:**
            - Single product content generation
            - Bulk CSV processing
            - Multiple tone options
            - Error resilience and recovery
            
            **Version:** 1.0.0
            """
        }
    )
    
    # Hide Streamlit style elements for cleaner UI
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)


def main():
    """
    Main entry point for the B2B AI E-commerce Content Generator application.
    
    This function initializes all components, sets up error handling and logging,
    and launches the Streamlit web interface.
    """
    # Record application start time
    import time
    start_time = time.time()
    
    try:
        # Setup Streamlit configuration
        setup_streamlit_config()
        
        # Store start time in session state
        if 'app_start_time' not in st.session_state:
            st.session_state.app_start_time = start_time
        
        # Initialize and run application
        app_manager = ApplicationManager()
        app_manager.run_application()
        
    except Exception as e:
        # Fallback error handling if ApplicationManager fails
        print(f"Critical startup error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Try to display error in Streamlit if possible
        try:
            st.error(f"❌ Critical startup error: {str(e)}")
            st.error("Please check the console output for detailed error information.")
            
            with st.expander("🔧 Troubleshooting Steps"):
                st.markdown("""
                1. **Check Configuration**: Ensure your `.env` file is properly configured
                2. **Verify Dependencies**: Run `pip install -r requirements.txt`
                3. **Check API Key**: Verify your OpenAI API key is valid
                4. **Restart Application**: Try restarting the application
                5. **Check Logs**: Review the `app.log` file for detailed error information
                """)
        except:
            # If Streamlit is not available, just print to console
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()