# Azure Terraform AI Agent

A web-based application that uses Azure OpenAI to generate Terraform scripts for Azure resources through natural language conversation.

## Features

- 🤖 Conversational interface powered by Azure OpenAI
- 🧠 AI-powered generation of Terraform code
- 🔍 Interactive prompting for missing information
- ✅ Terraform validation, planning, and deployment
- 🚀 Web-based interface for easy interaction

## Prerequisites

1. **Python 3.8+**
2. **Azure Subscription** with Azure OpenAI access
3. **Terraform CLI** installed (latest version recommended)
4. **Azure CLI** installed (optional, but recommended for authentication)

## Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/azure-terraform-ai-agent.git
   cd azure-terraform-ai-agent
   ```

2. **Create a virtual environment and install dependencies**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   Create a `.env` file with the following variables:

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

4. **Run the application**

   ```bash
   python terraform_ai_web.py
   ```

5. **Access the web interface**

   Open your browser and go to: http://localhost:5000

## Using the Agent

1. **Initialize the Agent**
   
   Click the "Connect to Azure OpenAI" button to start.

2. **Describe your infrastructure**
   
   Type your infrastructure requirements in natural language:
   
   Example: "Create a virtual network with a Linux VM in East US"

3. **Provide missing information**
   
   If the agent needs more details, it will prompt you with a form to input required information:
   
   - Subscription Name
   - Resource Group Name
   - Resource Name
   - Resource Type
   - Location

4. **Review generated Terraform code**
   
   The agent will generate Terraform code based on your complete requirements.

5. **Validate/Plan/Apply**
   
   Use the buttons to:
   
   - **Validate**: Check for syntax errors
   - **Plan**: Preview resource changes
   - **Apply**: Create the resources in Azure
   - **Destroy**: Remove all created resources

## Architecture

The application consists of several key components:

- **ConversationalAgent**: Handles dialogue with users and extracts infrastructure requirements
- **TerraformGenerator**: Creates Terraform HCL code from infrastructure specifications
- **TerraformExecutor**: Runs Terraform commands (validate, plan, apply, destroy)
- **Web Interface**: Provides a user-friendly front-end for interaction

## Troubleshooting

- **Connection issues**: Ensure your Azure OpenAI endpoint and API key are correct
- **Missing fields**: The agent will prompt for required information but may need more context
- **Terraform errors**: Check the execution output tab for detailed error messages

## Advanced Configuration

- **Custom Terraform Configuration**: Edit the generator's templates in `TerraformGenerator.generate_terraform_code`
- **Different Model**: Change the `AZURE_OPENAI_DEPLOYMENT` to use a different Azure OpenAI model
- **Alternate Regions**: Update the Azure region in your environment variables or provide it during conversation

## Security Considerations

- The application stores credentials in the `.env` file which should never be committed to version control
- Always run `terraform plan` before `terraform apply` to review changes
- Consider using more restrictive permissions for the Azure service principal
