#!/usr/bin/env python
import os
import argparse
import subprocess
import shutil
import sys

def check_requirements():
    """Check if required tools are installed."""
    print("Checking requirements...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("Error: Python 3.8 or higher is required.")
        return False
    
    # Check if pip is installed
    try:
        subprocess.run(["pip", "--version"], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: pip is not installed or not in the PATH.")
        return False
    
    # Check if Terraform is installed
    try:
        subprocess.run(["terraform", "--version"], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Warning: Terraform is not installed or not in the PATH.")
        print("You will need to install Terraform to apply infrastructure changes.")
        response = input("Do you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            return False
    
    # Check if Azure CLI is installed
    try:
        subprocess.run(["az", "--version"], check=True, capture_output=True)
        print("Azure CLI is installed.")
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Warning: Azure CLI is not installed or not in the PATH.")
        print("While not strictly required, Azure CLI can help with authentication.")
        print("Visit https://docs.microsoft.com/en-us/cli/azure/install-azure-cli for installation instructions.")
    
    return True

def create_directory_structure():
    """Create the directory structure for the application."""
    print("Creating directory structure...")
    
    # Check if we're in the right directory (where setup.py is)
    if not os.path.exists("setup.py"):
        print("Error: Please run this script from the directory containing setup.py")
        return False
    
    # Create directories
    dirs = ["templates", "static"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    
    return True

def create_env_file():
    """Create the .env file."""
    print("Creating .env file...")
    
    if os.path.exists(".env"):
        response = input(".env file already exists. Do you want to overwrite it? (y/n): ")
        if response.lower() != 'y':
            print("Skipping .env file creation.")
            return True
    
    subscription_id = input("Enter your Azure Subscription ID: ")
    tenant_id = input("Enter your Azure Tenant ID (press Enter to skip): ")
    client_id = input("Enter your Azure Client ID (press Enter to skip): ")
    client_secret = input("Enter your Azure Client Secret (press Enter to skip): ")
    
    # Azure OpenAI details
    openai_endpoint = input("Enter your Azure OpenAI endpoint (e.g., https://your-resource.openai.azure.com/): ")
    openai_api_key = input("Enter your Azure OpenAI API key: ")
    openai_api_version = input("Enter your Azure OpenAI API version (default: 2023-12-01-preview): ") or "2023-12-01-preview"
    openai_deployment = input("Enter your Azure OpenAI deployment name (default: gpt-4): ") or "gpt-4"
    
    env_content = f"""# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT={openai_endpoint}
AZURE_OPENAI_API_KEY={openai_api_key}
AZURE_OPENAI_API_VERSION={openai_api_version}
AZURE_OPENAI_DEPLOYMENT={openai_deployment}

# Azure configuration
AZURE_SUBSCRIPTION_ID={subscription_id}
AZURE_TENANT_ID={tenant_id}
AZURE_CLIENT_ID={client_id}
AZURE_CLIENT_SECRET={client_secret}

# Flask configuration
FLASK_SECRET_KEY={os.urandom(24).hex()}
FLASK_DEBUG=False

# Optional logging configuration
TF_LOG=INFO
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("Created .env file successfully.")
    return True

def install_dependencies():
    """Install Python dependencies."""
    print("Installing Python dependencies...")
    
    try:
        subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)
        print("Dependencies installed successfully.")
        return True
    except subprocess.SubprocessError as e:
        print(f"Error installing dependencies: {str(e)}")
        return False

def verify_azure_openai():
    """Verify Azure OpenAI settings."""
    print("Verifying Azure OpenAI settings...")
    
    # Check if we have the required Azure OpenAI environment variables
    if not os.path.exists(".env"):
        print("Warning: .env file does not exist. Cannot verify Azure OpenAI settings.")
        return True
    
    endpoint = None
    api_key = None
    deployment = None
    
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("AZURE_OPENAI_ENDPOINT="):
                endpoint = line.split("=")[1].strip()
            elif line.startswith("AZURE_OPENAI_API_KEY="):
                api_key = line.split("=")[1].strip()
            elif line.startswith("AZURE_OPENAI_DEPLOYMENT="):
                deployment = line.split("=")[1].strip()
    
    if not endpoint or not api_key:
        print("Warning: Azure OpenAI endpoint or API key is missing from .env file.")
        print("You will need to update the .env file with your Azure OpenAI credentials.")
        return True
    
    # Attempt to verify the Azure OpenAI endpoint and deployment
    try:
        import requests
        print(f"Verifying connection to Azure OpenAI at {endpoint}...")
        
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{endpoint}/openai/deployments?api-version=2023-12-01-preview",
            headers=headers
        )
        
        if response.status_code == 200:
            print("Successfully connected to Azure OpenAI!")
            
            # Check if the specified deployment is available
            deployments = response.json().get("data", [])
            deployment_names = [dep.get("id") for dep in deployments]
            
            if deployment and deployment in deployment_names:
                print(f"Deployment '{deployment}' is available.")
            elif deployment_names:
                print(f"Warning: Deployment '{deployment}' not found.")
                print(f"Available deployments: {', '.join(deployment_names)}")
                print(f"Please update the AZURE_OPENAI_DEPLOYMENT value in your .env file.")
            else:
                print("Warning: No deployments found in your Azure OpenAI resource.")
        else:
            print(f"Warning: Failed to connect to Azure OpenAI. Status code: {response.status_code}")
            print("Please check your Azure OpenAI credentials in the .env file.")
    
    except Exception as e:
        print(f"Warning: Failed to verify Azure OpenAI settings: {str(e)}")
        print("Please make sure your Azure OpenAI credentials are correct in the .env file.")
    
    return True

def create_templates():
    """Create templates for the web application."""
    print("Creating templates...")
    
    # Check if templates directory exists
    if not os.path.exists("templates"):
        print("Error: templates directory does not exist.")
        return False
    
    # Create index.html
    index_path = os.path.join("templates", "index.html")
    if os.path.exists(index_path):
        response = input("index.html already exists. Do you want to overwrite it? (y/n): ")
        if response.lower() != 'y':
            print("Skipping template creation.")
            return True
    
    # Copy the template file
    try:
        shutil.copy("templates_index.html", index_path)
        print("Created templates successfully.")
        return True
    except Exception as e:
        print(f"Error creating templates: {str(e)}")
        return False

def create_direct_run_script():
    """Create a direct run script."""
    print("Creating run script...")
    
    run_content = """#!/usr/bin/env python
import os
from dotenv import load_dotenv
from terraform_ai_web import app

# Load environment variables
load_dotenv()

if __name__ == '__main__':
    # Set default port or get from environment
    port = int(os.getenv("PORT", 5000))
    
    # Debug mode for development
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    app.run(host='0.0.0.0', port=port, debug=debug)
"""
    
    with open("run.py", "w") as f:
        f.write(run_content)
    
    # Make it executable
    os.chmod("run.py", 0o755)
    
    print("Created run.py script.")
    return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Setup the Azure Terraform AI Agent web interface")
    parser.add_argument("--skip-checks", action="store_true", help="Skip dependency checks")
    parser.add_argument("--skip-openai-verify", action="store_true", help="Skip Azure OpenAI verification")
    args = parser.parse_args()
    
    print("Setting up Azure Terraform AI Agent web interface...")
    
    if not args.skip_checks and not check_requirements():
        print("Requirements check failed. Please install the required tools and try again.")
        return 1
    
    if not create_directory_structure():
        print("Failed to create directory structure.")
        return 1
    
    if not create_env_file():
        print("Failed to create .env file.")
        return 1
    
    if not install_dependencies():
        print("Failed to install dependencies.")
        return 1
    
    if not args.skip_openai_verify and not verify_azure_openai():
        print("Failed to verify Azure OpenAI settings.")
        # Continue anyway
    
    if not create_templates():
        print("Failed to create templates.")
        return 1
    
    if not create_direct_run_script():
        print("Failed to create run script.")
        return 1
    
    print("\nSetup completed successfully!")
    print("You can now run the web interface with: python run.py")
    print("The web interface will be available at: http://localhost:5000")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())