#!/usr/bin/env python3
"""
Startup Script for B2B AI E-commerce Content Generator

This script provides a convenient way to start the application with
proper configuration and environment setup.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def check_requirements():
    """Check if all required dependencies are installed."""
    try:
        import streamlit
        import openai
        import pandas
        print("✅ All required dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install requirements with: pip install -r requirements.txt")
        return False


def check_configuration():
    """Check if configuration is properly set up."""
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment variables only")
    
    # Check for required configuration
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key or api_key == 'your_openai_api_key_here':
        print("⚠️  OpenAI API key not configured")
        print("Please set your OPENAI_API_KEY in the .env file")
        print("See setup_instructions.md for details")
        return False
    
    print("✅ Configuration appears to be set up correctly")
    return True


def create_env_file_if_missing():
    """Create .env file from example if it doesn't exist."""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists() and env_example.exists():
        print("📝 Creating .env file from .env.example")
        with open(env_example, 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print("✅ .env file created. Please edit it with your API key.")
        return False
    
    return env_file.exists()


def run_application(port=8501, host='localhost', debug=False):
    """Run the Streamlit application."""
    # Set environment variables
    if debug:
        os.environ['APP_ENV'] = 'development'
        os.environ['DEBUG'] = 'true'
    
    # Construct streamlit command
    cmd = [
        sys.executable, '-m', 'streamlit', 'run', 'main.py',
        '--server.port', str(port),
        '--server.address', host,
        '--server.headless', 'false',
        '--browser.gatherUsageStats', 'false'
    ]
    
    if debug:
        cmd.extend(['--logger.level', 'debug'])
    
    print(f"🚀 Starting application on http://{host}:{port}")
    print("Press Ctrl+C to stop the application")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        return False
    
    return True


def main():
    """Main entry point for the startup script."""
    parser = argparse.ArgumentParser(
        description='B2B AI E-commerce Content Generator Startup Script'
    )
    parser.add_argument(
        '--port', '-p', 
        type=int, 
        default=8501,
        help='Port to run the application on (default: 8501)'
    )
    parser.add_argument(
        '--host', 
        default='localhost',
        help='Host to bind the application to (default: localhost)'
    )
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Run in debug mode with verbose logging'
    )
    parser.add_argument(
        '--check-only', '-c',
        action='store_true',
        help='Only check requirements and configuration, do not start the app'
    )
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Run setup wizard to configure the application'
    )
    
    args = parser.parse_args()
    
    print("🛍️  B2B AI E-commerce Content Generator")
    print("=" * 50)
    
    # Run setup wizard if requested
    if args.setup:
        run_setup_wizard()
        return
    
    # Check requirements
    if not check_requirements():
        print("\n💡 Install requirements with: pip install -r requirements.txt")
        return
    
    # Create .env file if missing
    if not create_env_file_if_missing():
        print("\n💡 Please edit the .env file with your OpenAI API key and run again")
        return
    
    # Check configuration
    config_ok = check_configuration()
    
    if args.check_only:
        if config_ok:
            print("\n✅ All checks passed! Ready to run the application.")
        else:
            print("\n❌ Configuration issues found. Please fix them before running.")
        return
    
    if not config_ok:
        print("\n⚠️  Configuration issues detected, but starting anyway...")
        print("You can fix configuration issues in the web interface.")
    
    # Run the application
    success = run_application(args.port, args.host, args.debug)
    
    if success:
        print("\n✅ Application started successfully")
    else:
        print("\n❌ Failed to start application")


def run_setup_wizard():
    """Run interactive setup wizard."""
    print("\n🧙 Setup Wizard")
    print("=" * 20)
    
    # Check if .env file exists
    env_file = Path('.env')
    if not env_file.exists():
        create_env_file_if_missing()
    
    # Get OpenAI API key
    current_key = os.getenv('OPENAI_API_KEY', '')
    if current_key and current_key != 'your_openai_api_key_here':
        print(f"✅ OpenAI API key is already configured: {current_key[:8]}...")
        update_key = input("Do you want to update it? (y/N): ").lower().strip()
        if update_key != 'y':
            print("✅ Keeping existing API key")
            return
    
    print("\n🔑 OpenAI API Key Setup")
    print("You need an OpenAI API key to use this application.")
    print("Get one at: https://platform.openai.com/api-keys")
    
    api_key = input("\nEnter your OpenAI API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Setup cancelled.")
        return
    
    if not api_key.startswith('sk-'):
        print("⚠️  Warning: OpenAI API keys typically start with 'sk-'")
        confirm = input("Continue anyway? (y/N): ").lower().strip()
        if confirm != 'y':
            print("Setup cancelled.")
            return
    
    # Update .env file
    try:
        # Read current .env file
        env_content = ""
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_content = f.read()
        
        # Update or add API key
        lines = env_content.split('\n')
        updated = False
        
        for i, line in enumerate(lines):
            if line.startswith('OPENAI_API_KEY='):
                lines[i] = f'OPENAI_API_KEY={api_key}'
                updated = True
                break
        
        if not updated:
            lines.append(f'OPENAI_API_KEY={api_key}')
        
        # Write back to file
        with open(env_file, 'w') as f:
            f.write('\n'.join(lines))
        
        print("✅ API key saved to .env file")
        
        # Test the configuration
        print("\n🧪 Testing configuration...")
        os.environ['OPENAI_API_KEY'] = api_key
        
        if check_configuration():
            print("✅ Setup completed successfully!")
            print("\nYou can now run the application with: python run.py")
        else:
            print("⚠️  Setup completed but there may be configuration issues.")
    
    except Exception as e:
        print(f"❌ Failed to save configuration: {e}")


if __name__ == "__main__":
    main()