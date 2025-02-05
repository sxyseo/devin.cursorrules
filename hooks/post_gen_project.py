import os
import shutil
import platform

def setup_env_file():
    """Set up the .env file with API key if provided"""
    llm_api_key = '{{ cookiecutter.llm_api_key.default }}'  # Access the default value
    
    # Add API key if provided
    if llm_api_key:
        with open('.env', 'a') as f:  # Append mode
            f.write(f'\nLLM_API_KEY={llm_api_key}\n')

def main():
    print("\nInitial debug info:")
    print(f"- Current working directory: {os.getcwd()}")
    print(f"- Directory contents: {os.listdir('.')}")
    
    # Set up environment file
    print("\nSetting up .env file...")
    setup_env_file()
    
    # Create virtual environment
    print("\nCreating virtual environment...")
    os.system('python -m venv venv')
    
    # Install dependencies
    print("\nInstalling dependencies...")
    if platform.system() == 'Windows':
        os.system('venv\\Scripts\\pip install -r requirements.txt')
    else:
        os.system('venv/bin/pip install -r requirements.txt')
    
    print("\nSetup completed successfully!")
    print("To get started:")
    print("1. Activate your virtual environment:")
    if platform.system() == 'Windows':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("2. Check the README.md file for more information")

if __name__ == '__main__':
    main() 