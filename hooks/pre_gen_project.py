import re
import sys

# Get user input variables
project_name = '{{ cookiecutter.project_name }}'
project_type = '{{ cookiecutter.project_type }}'
llm_api_key = '{{ cookiecutter.llm_api_key }}'

# Validate project name
if not re.match(r'^[a-z][-a-z0-9]+$', project_name):
    print('ERROR: Project name must start with a letter and contain only lowercase letters, numbers, and hyphens.')
    sys.exit(1)

# Validate project type
if project_type not in ['cursor', 'windsurf']:
    print('ERROR: Project type must be either "cursor" or "windsurf".')
    sys.exit(1)

# API key is optional, no validation needed 