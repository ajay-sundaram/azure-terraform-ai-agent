# Azure Terraform AI Agent

A web-based application that uses Anthropic Claude AI to generate Terraform scripts for Azure resources through natural language conversation.

## Features

- 🤖 Conversational interface powered by Claude AI
- 🧠 AI-powered generation of Terraform code
- 🔍 Interactive prompting for missing information
- ✅ Terraform validation, planning, and deployment
- 🚀 Web-based interface for easy interaction

## Prerequisites

1. **Python 3.8+**
2. **Azure Subscription**
3. **Terraform CLI** installed (latest version recommended)
4. **Azure CLI** installed (optional, but recommended for authentication)
5. Anthropic Claude AI subscription with API Key

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
   
3. **Run the application**

   ```bash
   python terraform_ai_web.py
   ```

4. **Access the web interface**

   Open your browser and go to: http://localhost:5000
