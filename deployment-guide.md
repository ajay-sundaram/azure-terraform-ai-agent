# Deployment Guide for Terraform AI Agent

This guide walks you through deploying and configuring the Azure Terraform AI Agent which now includes functionality to prompt for missing information.

## Project Structure

Ensure your project directory contains these files:

```
azure-terraform-ai-agent/
├── .env                      # Environment variables
├── requirements.txt          # Python dependencies
├── azure_terraform_agent.py  # Main agent code
├── terraform_ai_web.py       # Web interface
└── templates/
    └── index.html            # HTML template
```

## Step 1: Prepare Azure OpenAI

1. **Create an Azure OpenAI resource**:
   - Navigate to the [Azure Portal](https://portal.azure.com)
   - Search for "Azure OpenAI"
   - Create a new OpenAI resource
   - Note the endpoint URL

2. **Deploy a model**:
   - In your Azure OpenAI resource, go to "Model deployments"
   - Deploy a GPT-4 or GPT-3.5-Turbo model
   - Name your deployment (e.g., "gpt-4")
   - Copy the deployment name

3. **Get API credentials**:
   - In your Azure OpenAI resource, go to "Keys and Endpoint"
   - Copy one of the keys (KEY1 or KEY2)
   - Note your endpoint URL

## Step 2: Set Up Azure Authentication

You need Azure credentials for Terraform to deploy resources:

1. **Service Principal (recommended)**:
   ```bash
   az login
   az account set --subscription "Your Subscription Name"
   az ad sp create-for-rbac --name "TerraformAIAgent" --role Contributor
   ```
   
   Note the output values:
   - `appId` is your AZURE_CLIENT_ID
   - `password` is your AZURE_CLIENT_SECRET
   - `tenant` is your AZURE_TENANT_ID

2. **Get Subscription ID**:
   ```bash
   az account show --query id -o tsv
   ```
   This is your AZURE_SUBSCRIPTION_ID

## Step 3: Install Dependencies

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Step 4: Configure Environment

Create a `.env` file with your credentials:

```
# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_DEPLOYMENT=your-deployment-name

# Azure configuration
AZURE_SUBSCRIPTION_ID=your_subscription_id_here
AZURE_TENANT_ID=your_tenant_id_here
AZURE_CLIENT_ID=your_client_id_here
AZURE_CLIENT_SECRET=your_client_secret_here

# Flask configuration
FLASK_SECRET_KEY=generate_a_random_secret_key
FLASK_DEBUG=False
```

You can generate a random secret key with:
```python
import os
print(os.urandom(24).hex())
```

## Step 5: Install Terraform

1. **Download Terraform**:
   - Go to [Terraform Downloads](https://www.terraform.io/downloads)
   - Download the appropriate version for your OS
   - Extract the executable to a directory in your PATH

2. **Verify installation**:
   ```bash
   terraform --version
   ```

## Step 6: Launch the Application

1. **Start the web server**:
   ```bash
   python terraform_ai_web.py
   ```

2. **Access the web interface**:
   - Open your browser
   - Navigate to http://localhost:5000

## Step 7: Using the New Missing Information Feature

When you interact with the agent, it may determine it needs more information:

1. **Initial request**:
   - Enter a request like "Create a virtual machine in Azure"

2. **Missing information prompt**:
   - The agent will identify that it needs more information
   - A form will appear asking for specifics (subscription name, resource group, etc.)
   - Fill in the fields and submit

3. **Terraform generation**:
   - After you provide the missing information, the agent will generate the Terraform code
   - Review the code in the "Terraform Code" tab

4. **Execute Terraform operations**:
   - Use the buttons to validate, plan, apply, or destroy

## Troubleshooting

### Connection Issues

If you can't connect to Azure OpenAI:
- Verify your endpoint URL ends with a trailing slash
- Check that your API key is correct
- Ensure your deployment name exists and is active
- Try using the API version parameter: `AZURE_OPENAI_API_VERSION=2023-05-15`

### Missing Fields Not Appearing

If the missing fields form doesn't appear:
- Check the browser console for JavaScript errors
- Ensure the system message from the agent contains "needs_more_info: true"
- Verify that missing_fields is an array in the response

### Terraform Execution Failures

If Terraform operations fail:
- Check that Terraform is in your PATH
- Verify your Azure credentials
- Look at the execution output tab for detailed error messages
- Make sure you have permissions to create resources

## Production Deployment Considerations

For production deployments:
- Use a proper web server like Gunicorn or uWSGI
- Set up HTTPS with proper certificates
- Deploy behind a reverse proxy like Nginx
- Implement proper authentication

Example Docker setup:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "terraform_ai_web:app"]
```