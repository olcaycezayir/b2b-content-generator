# Setup Instructions

## Development Environment Setup

### 1. Python Environment

Ensure you have Python 3.8 or higher installed:

```bash
python --version
```

### 2. Virtual Environment (Recommended)

Create and activate a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

Install all required packages:

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit the `.env` file with your configuration:

```bash
# Required: Add your OpenAI API key
OPENAI_API_KEY=sk-your-actual-api-key-here

# Optional: Customize other settings
APP_ENV=development
DEBUG=true
MAX_FILE_SIZE_MB=50
CSV_CHUNK_SIZE=100
```

### 5. Verify Installation

Test that all dependencies are correctly installed:

```bash
python -c "import streamlit, openai, pandas, dotenv, hypothesis, PIL; print('All dependencies installed successfully!')"
```

## Running the Application

### Development Mode

Start the Streamlit development server:

```bash
streamlit run ui.py
```

The application will be available at: http://localhost:8501

### Production Mode

For production deployment, set environment variables:

```bash
export APP_ENV=production
export DEBUG=false
streamlit run ui.py --server.port 8501 --server.address 0.0.0.0
```

## Testing Setup

### Unit Tests

Install testing dependencies (included in requirements.txt):

- pytest
- hypothesis

Run tests:

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=.

# Run specific test file
python -m pytest tests/test_content_generator.py
```

### Property-Based Tests

Property-based tests use Hypothesis framework:

```bash
# Run only property tests
python -m pytest -k "property"

# Run with verbose output
python -m pytest -v -k "property"
```

## Configuration Options

### Environment Variables

| Variable           | Description                | Default     | Required |
| ------------------ | -------------------------- | ----------- | -------- |
| `OPENAI_API_KEY`   | OpenAI API key             | None        | Yes      |
| `APP_ENV`          | Application environment    | development | No       |
| `DEBUG`            | Enable debug mode          | true        | No       |
| `MAX_FILE_SIZE_MB` | Max CSV file size          | 50          | No       |
| `CSV_CHUNK_SIZE`   | Batch processing size      | 100         | No       |
| `MAX_RETRIES`      | API retry attempts         | 3           | No       |
| `RETRY_DELAY_BASE` | Base retry delay (seconds) | 1.0         | No       |
| `RATE_LIMIT_DELAY` | Rate limit delay (seconds) | 60          | No       |

### Streamlit Configuration

Create `.streamlit/config.toml` for custom Streamlit settings:

```toml
[server]
port = 8501
address = "0.0.0.0"

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[browser]
gatherUsageStats = false
```

## Troubleshooting

### Common Setup Issues

**1. Import Errors**

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

**2. OpenAI API Key Issues**

```bash
# Verify API key is set
python -c "import os; print('API Key:', os.getenv('OPENAI_API_KEY', 'NOT SET'))"

# Test API connection
python -c "from openai import OpenAI; client = OpenAI(); print('API connection successful')"
```

**3. Streamlit Port Conflicts**

```bash
# Use different port
streamlit run ui.py --server.port 8502

# Kill existing processes
pkill -f streamlit
```

**4. File Permission Issues**

```bash
# Ensure proper permissions
chmod +x setup_instructions.md
chmod 644 .env
```

### Development Tips

1. **Hot Reloading**: Streamlit automatically reloads when files change
2. **Debug Mode**: Set `DEBUG=true` in `.env` for detailed error messages
3. **Logging**: Check console output for detailed application logs
4. **Memory Usage**: Monitor memory usage during bulk processing

### IDE Setup

**VS Code Extensions:**

- Python
- Streamlit
- Python Docstring Generator

**PyCharm Configuration:**

- Set Python interpreter to virtual environment
- Configure run configuration for Streamlit

## Deployment

### Local Deployment

```bash
# Production mode
export APP_ENV=production
streamlit run ui.py --server.port 8501
```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "ui.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

Build and run:

```bash
docker build -t b2b-content-generator .
docker run -p 8501:8501 --env-file .env b2b-content-generator
```

### Cloud Deployment

**Streamlit Cloud:**

1. Push code to GitHub
2. Connect repository to Streamlit Cloud
3. Add secrets in Streamlit Cloud dashboard

**Heroku:**

1. Create `Procfile`: `web: streamlit run ui.py --server.port $PORT`
2. Set environment variables in Heroku dashboard
3. Deploy using Git or GitHub integration

## Next Steps

After setup completion:

1. **Test the application** with sample data
2. **Review the code structure** in each module
3. **Run the test suite** to ensure everything works
4. **Customize configuration** for your specific needs
5. **Start development** following the implementation plan

For development workflow, see the main README.md file.
