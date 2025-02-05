import os
import shutil
import platform

def find_project_root():
    """Find the original project root directory by walking up until we find the template directory"""
    current = os.getcwd()
    parent = os.path.dirname(current)  # Go up one level to find template dir
    template_dir = os.path.join(parent, 'template')
    if os.path.exists(template_dir):
        return parent
    raise Exception(f"Could not find project root directory. Current: {current}, Parent: {parent}")

def copy_tools_directory():
    """Copy the tools directory from project root"""
    try:
        project_root = find_project_root()
        source_tools = os.path.join(project_root, 'tools')
        if os.path.exists(source_tools):
            print(f"\nCopying tools directory...")
            print(f"- Source: {source_tools}")
            print(f"- Destination: tools")
            shutil.copytree(source_tools, 'tools', dirs_exist_ok=True)
            print("Tools directory copied successfully")
        else:
            print(f"Warning: Tools directory not found at {source_tools}")
    except Exception as e:
        print(f"Error copying tools directory: {str(e)}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Directory contents of parent: {os.listdir('..')}")
        raise

def setup_env_file():
    """Set up the .env file with API key if provided"""
    llm_api_key = '{{ cookiecutter.llm_api_key.default }}'  # Access the default value
    if llm_api_key:
        with open('.env', 'w') as f:
            f.write(f'LLM_API_KEY={llm_api_key}\n')
    else:
        # Copy .env.example if exists
        if os.path.exists('.env.example'):
            shutil.copy2('.env.example', '.env')

def main():
    print("\nInitial debug info:")
    print(f"- Current working directory: {os.getcwd()}")
    print(f"- Parent directory: {os.path.dirname(os.getcwd())}")
    print(f"- Directory contents: {os.listdir('.')}")
    
    # Copy tools directory
    copy_tools_directory()
    
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