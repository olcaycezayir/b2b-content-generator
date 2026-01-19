# B2B AI E-commerce Content Generator

A comprehensive web application that automates product listing creation for e-commerce sellers using AI technology. Generate SEO-optimized titles, creative descriptions, and social media hashtags for both single products and bulk processing from CSV files.

## 🚀 Quick Start

### Option 1: Using the Startup Script (Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Run setup wizard to configure API key
python run.py --setup

# Start the application
python run.py
```

### Option 2: Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env file with your OpenAI API key
# OPENAI_API_KEY=your_actual_api_key_here

# Start the application
streamlit run main.py
```

## 📋 Features

### ✨ Single Product Mode

- **Image Upload**: Upload product images for AI analysis
- **Text Input**: Enter product names and descriptions
- **Tone Selection**: Choose from 5 different content tones
- **Real-time Generation**: Get instant SEO-optimized content
- **Interactive Editing**: Edit and refine generated content
- **Export Options**: Copy, download, or validate content

### 📊 Bulk Processing Mode

- **CSV Upload**: Process multiple products from CSV files
- **Progress Tracking**: Real-time progress indicators
- **Error Resilience**: Continue processing despite individual failures
- **Memory Efficient**: Chunked processing for large files
- **Detailed Reports**: Comprehensive processing analytics
- **Quality Analysis**: Content validation and statistics

### 🛠️ Advanced Features

- **Comprehensive Error Handling**: Graceful error recovery and user-friendly messages
- **Performance Monitoring**: Real-time metrics and system health monitoring
- **Logging System**: Structured logging with multiple levels and file rotation
- **Configuration Management**: Environment-based configuration with validation
- **Session Management**: Automatic state preservation across UI interactions

## 🏗️ Architecture

The application follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   UI Layer      │    │ Business Logic  │    │ Service Layer   │
│                 │    │                 │    │                 │
│ • Streamlit UI  │◄──►│ Content Gen.    │◄──►│ LLM Service     │
│ • Single Mode   │    │ CSV Processor   │    │ Config Manager  │
│ • Bulk Mode     │    │ Data Validator  │    │ Error Handler   │
│ • Monitoring    │    │                 │    │ Logging System  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

- **`main.py`**: Application entry point with service initialization and wiring
- **`ui.py`**: Streamlit user interface with single and bulk processing modes
- **`content_generator.py`**: Core AI content generation logic
- **`llm_service.py`**: OpenAI API integration with retry logic and error handling
- **`csv_processor.py`**: Bulk file processing with memory efficiency
- **`utils.py`**: Data models, validation, configuration, and error handling
- **`logging_config.py`**: Comprehensive logging configuration
- **`monitoring.py`**: Performance monitoring and system health checks

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional
APP_ENV=development                # development, production, test
DEBUG=true                        # Enable debug logging
MAX_FILE_SIZE_MB=50              # Maximum CSV file size
CSV_CHUNK_SIZE=100               # Rows per processing chunk
MAX_RETRIES=3                    # API retry attempts
RETRY_DELAY_BASE=1.0             # Base retry delay in seconds
RATE_LIMIT_DELAY=60              # Rate limit delay in seconds
```

### Tone Profiles

The application supports 5 content tones:

- **Professional**: Formal, business-focused language
- **Casual**: Friendly, conversational tone
- **Luxury**: Sophisticated, high-end positioning
- **Energetic**: Dynamic, exciting language
- **Minimalist**: Clean, simple, direct language

## 📊 Monitoring & Analytics

### Development Mode Features

- **Real-time Metrics**: Request counts, error rates, performance data
- **System Health**: Service status, API connectivity, resource usage
- **Performance Analytics**: Operation timing, success rates, bottleneck identification
- **Log Viewer**: Access to application logs through the web interface

### Production Monitoring

- **Structured Logging**: JSON-formatted logs for external monitoring systems
- **Health Checks**: Automated system health verification
- **Performance Metrics**: Detailed operation timing and success tracking
- **Error Tracking**: Comprehensive error logging with context

## 🧪 Testing

The application includes comprehensive testing capabilities:

```bash
# Run unit tests
python -m pytest tests/ -v

# Run property-based tests
python -m pytest tests/ -k "property" -v

# Run integration tests
python -m pytest tests/test_integration.py -v

# Check test coverage
python -m pytest tests/ --cov=. --cov-report=html
```

## 📁 File Structure

```
├── main.py                    # Application entry point
├── ui.py                      # Streamlit user interface
├── content_generator.py       # Core content generation
├── llm_service.py            # OpenAI API integration
├── csv_processor.py          # Bulk processing logic
├── utils.py                  # Utilities and data models
├── logging_config.py         # Logging configuration
├── monitoring.py             # Performance monitoring
├── run.py                    # Startup script
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── setup_instructions.md    # Detailed setup guide
├── tests/                   # Test suite
│   ├── test_ui.py
│   ├── test_content_generator.py
│   ├── test_llm_service.py
│   ├── test_csv_processor.py
│   └── test_utils.py
└── logs/                    # Application logs (created at runtime)
```

## 🚨 Error Handling

The application implements comprehensive error handling:

- **API Errors**: Automatic retry with exponential backoff
- **Rate Limiting**: Graceful handling of API quotas
- **File Errors**: Validation and user-friendly error messages
- **Network Issues**: Connection retry and fallback mechanisms
- **Partial Results**: Recovery from incomplete operations

## 🔒 Security

- **Input Sanitization**: XSS and injection attack prevention
- **API Key Protection**: Secure configuration management
- **File Validation**: Size limits and format restrictions
- **Error Masking**: Sensitive information protection in logs

## 📈 Performance

- **Memory Efficiency**: Chunked processing for large files
- **Streaming**: Memory-conscious CSV processing
- **Caching**: Session state management for UI responsiveness
- **Monitoring**: Real-time performance tracking

## 🛠️ Development

### Running in Development Mode

```bash
# Start with debug logging
python run.py --debug

# Check configuration only
python run.py --check-only

# Access monitoring dashboard
# Available in sidebar when running in development mode
```

### Adding New Features

1. **UI Components**: Add to `ui.py` following the existing patterns
2. **Business Logic**: Extend `content_generator.py` or create new modules
3. **Services**: Add to service layer with proper error handling
4. **Monitoring**: Use decorators for automatic performance tracking

### Configuration Management

The application uses a centralized configuration system:

```python
from utils import ConfigurationManager

config = ConfigurationManager()
api_key = config.get_config_value('OPENAI_API_KEY')
chunk_size = config.get_int_config('CSV_CHUNK_SIZE', 100)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Setup Issues**: See `setup_instructions.md`
- **Configuration**: Use the setup wizard: `python run.py --setup`
- **Monitoring**: Access the monitoring dashboard in development mode
- **Logs**: Check the `logs/` directory for detailed error information

## 🔄 Updates

The application includes automatic health checks and monitoring to ensure optimal performance. Regular updates include:

- Performance optimizations
- Enhanced error handling
- New content generation features
- Improved monitoring capabilities
