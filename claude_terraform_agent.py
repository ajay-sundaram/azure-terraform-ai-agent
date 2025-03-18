import os
import json
import logging
import uuid
import tempfile
import subprocess
import re
import requests
from typing import Dict, List, Optional, Tuple, Any
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.core.exceptions import ResourceNotFoundError
import anthropic

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConversationalAgent:
    """
    Handles conversations with users and interprets their intents for cloud infrastructure operations.
    Uses Claude AI for model inference.
    """
    
    def __init__(self, 
                 anthropic_api_key: Optional[str] = None,
                 model: Optional[str] = None):
        """
        Initialize the conversational agent.
        
        Args:
            anthropic_api_key: Anthropic API key. If None, it will try to get from environment variable.
            model: The Claude model to use. If None, it will use the default.
        """
        # Set Anthropic configuration
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Please provide it or set ANTHROPIC_API_KEY environment variable.")
        
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        self.conversation_history = []
        
        # Example system message to guide the model behavior
        self.system_message = """
        You are an AI assistant that helps users create and manage cloud infrastructure on Azure using Terraform.
        Your task is to interpret user requests for cloud infrastructure and translate them into detailed specifications.
        
        Required details for any infrastructure request:
        - Subscription Name
        - Resource Group Name
        - Resource Name
        - Resource Type
        - Location 
        
        When a user requests infrastructure, extract the following information:
        1. Resource types (e.g., VMs, storage, network components)
        2. Resource specifications (e.g., VM sizes, storage capacities)
        3. Relationships between resources
        4. Resource Group Name and Location
        5. Subscription name
        
        If ANY details are missing, you need to ask the user for these specific details before continuing.
        
        When you have all required information, respond with a valid JSON object containing the infrastructure specifications.
        Format your JSON like this:
        ```json
        {
          "subscription_name": "...",
          "resource_group": "...",
          "resource_name": "...",
          "resource_type": "...",
          "location": "...",
          "additional_properties": { ... }
        }
        ```
        """
        
    def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and extract infrastructure requirements.
        
        Args:
            user_message: The message from the user.
            
        Returns:
            A dictionary containing the interpreted infrastructure requirements or missing fields info.
        """
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Call Anthropic API to get response
        try:
            response = self.client.messages.create(
                model=self.model,
                system=self.system_message,
                messages=self.conversation_history,
                temperature=0.2,
                max_tokens=1024
            )
            
            # Extract the text response
            assistant_message = response.content[0].text
            
            # Add the assistant's message to history
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Check if the response is asking for more information
            missing_fields_pattern = r"need.+?(?:information|details)|missing.+?(?:information|details)|provide.+?(?:information|details)"
            asking_for_info = re.search(missing_fields_pattern, assistant_message, re.IGNORECASE)
            
            # Process the response
            if asking_for_info:
                # Extract which fields are being requested
                missing_fields = []
                if "subscription" in assistant_message.lower():
                    missing_fields.append("subscription_name")
                if "resource group" in assistant_message.lower():
                    missing_fields.append("resource_group")
                if "resource name" in assistant_message.lower():
                    missing_fields.append("resource_name")
                if "resource type" in assistant_message.lower():
                    missing_fields.append("resource_type")
                if "location" in assistant_message.lower():
                    missing_fields.append("location")
                
                # If no specific fields were detected, ask for all
                if not missing_fields:
                    missing_fields = ["subscription_name", "resource_group", "resource_name", "resource_type", "location"]
                
                return {
                    "needs_more_info": True,
                    "missing_fields": missing_fields,
                    "message": assistant_message
                }
            
            # Try to parse JSON from the response
            try:
                # Look for JSON content in the message
                json_match = re.search(r'```json\s*(.*?)\s*```', assistant_message, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                    infrastructure_spec = json.loads(json_content)
                else:
                    # Try to find JSON content without code block markers
                    json_start = assistant_message.find('{')
                    json_end = assistant_message.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_content = assistant_message[json_start:json_end]
                        infrastructure_spec = json.loads(json_content)
                    else:
                        # If no JSON found, check for missing fields in the response
                        required_fields = ["subscription_name", "resource_group", "resource_name", "resource_type", "location"]
                        # Check which fields are mentioned in the message to determine what's missing
                        missing_fields = [field for field in required_fields if field.replace("_", " ") in assistant_message.lower()]
                        
                        if missing_fields:
                            return {
                                "needs_more_info": True,
                                "missing_fields": missing_fields,
                                "message": assistant_message
                            }
                        else:
                            # Request all fields if we can't determine specific missing ones
                            return {
                                "needs_more_info": True,
                                "missing_fields": required_fields,
                                "message": "To generate the Terraform code, I need the following details:\n\n- Subscription Name\n- Resource Group Name\n- Resource Name\n- Resource Type\n- Location (Azure region)"
                            }
                
                # Check if parsed JSON has all required fields
                required_fields = ["subscription_name", "resource_group", "resource_name", "resource_type", "location"]
                missing_fields = [field for field in required_fields if field not in infrastructure_spec or not infrastructure_spec[field]]
                
                if missing_fields:
                    return {
                        "needs_more_info": True,
                        "missing_fields": missing_fields,
                        "message": f"I still need the following information: {', '.join(field.replace('_', ' ').title() for field in missing_fields)}"
                    }
                
                return infrastructure_spec
                
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response from assistant")
                # If JSON parsing fails, check if the response is asking for more information
                required_fields = ["subscription_name", "resource_group", "resource_name", "resource_type", "location"]
                
                # If it seems to be asking for more info but we couldn't parse it properly
                return {
                    "needs_more_info": True,
                    "missing_fields": required_fields,
                    "message": "I need more information to generate the Terraform code. Please provide all of these details:\n\n- Subscription Name\n- Resource Group Name\n- Resource Name\n- Resource Type\n- Location (Azure region)"
                }
                    
        except Exception as e:
            logger.error(f"Failed to call Claude API: {str(e)}")
            return {
                "error": f"Failed to call Claude API: {str(e)}",
                "raw_response": ""
            }
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Get the conversation history.
        
        Returns:
            The conversation history.
        """
        return self.conversation_history
    
    def clear_conversation_history(self) -> None:
        """
        Clear the conversation history, keeping only the system message.
        """
        self.conversation_history = [self.conversation_history[0]]

class TerraformGenerator:
    """
    Generates Terraform HCL code based on infrastructure specifications.
    Uses Claude AI for model inference.
    """
    
    def __init__(self, 
                 anthropic_api_key: Optional[str] = None,
                 model: Optional[str] = None):
        """
        Initialize the Terraform code generator.
        
        Args:
            anthropic_api_key: Anthropic API key. If None, it will try to get from environment variable.
            model: The Claude model to use. If None, it will use the default.
        """
        # Set Anthropic configuration
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Please provide it or set ANTHROPIC_API_KEY environment variable.")
        
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def generate_terraform_code(self, infrastructure_spec: Dict[str, Any]) -> str:
        """
        Generate Terraform HCL code based on the infrastructure specification.
        
        Args:
            infrastructure_spec: The infrastructure specification dictionary.
            
        Returns:
            The generated Terraform HCL code as a string.
        """
        # Prepare a detailed prompt for the Claude model to generate Terraform code
        system_prompt = "You are an expert Terraform developer specializing in Azure infrastructure."
        
        user_prompt = f"""
        Generate complete, valid Terraform HCL code for Azure to implement the following infrastructure specification:
        
        {json.dumps(infrastructure_spec, indent=2)}
        
        Include:
        1. Provider configuration for Azure
        2. Resource group definition
        3. All required resources with appropriate configurations
        4. Output definitions for important resource identifiers
        
        Use terraform best practices, including:
        - Proper variable declarations
        - Resource naming conventions
        - Use of locals where appropriate
        - Organized file structure (provider.tf, variables.tf, main.tf, outputs.tf)
        
        Return ONLY the Terraform code, grouped by file, with each file name as a markdown header.
        Format the code with proper Terraform code blocks like:
        
        # provider.tf
        ```hcl
        provider "azurerm" {{
          features {{}}
        }}
        ```
        
        # main.tf
        ```hcl
        // Terraform code
        ```
        """
        
        try:
            # Call Anthropic API to generate Terraform code
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.2,
                max_tokens=4000
            )
            
            # Extract the generated Terraform code
            terraform_code = response.content[0].text
            
            return terraform_code
            
        except Exception as e:
            logger.error(f"Failed to call Claude API: {str(e)}")
            return f"Error generating Terraform code: {str(e)}"
    
    def parse_terraform_files(self, terraform_code: str) -> Dict[str, str]:
        """
        Parse the generated Terraform code into separate files.
        
        Args:
            terraform_code: The Terraform code as a single string with markdown headers.
            
        Returns:
            A dictionary mapping file names to their content.
        """
        files = {}
        current_file = None
        current_content = []
        in_code_block = False
        
        # Split the code by lines
        lines = terraform_code.strip().split('\n')
        
        for line in lines:
            # Check if the line is a markdown header (file name)
            header_match = re.match(r'^#+\s+(.+\.tf)$', line)
            if header_match:
                # Save the previous file if there was one
                if current_file and current_content:
                    files[current_file] = '\n'.join(current_content)
                
                # Start a new file
                current_file = header_match.group(1)
                current_content = []
                in_code_block = False
            elif line.strip().startswith('```') and not in_code_block:
                # Start of code block - skip this line
                in_code_block = True
            elif line.strip().startswith('```') and in_code_block:
                # End of code block - skip this line
                in_code_block = False
            elif current_file and in_code_block:
                # We're inside a code block for the current file - add the line
                current_content.append(line)
        
        # Save the last file
        if current_file and current_content:
            files[current_file] = '\n'.join(current_content)
        
        # If no files were found using markdown headers, assume it's a single file
        if not files:
            # Try to extract content from code blocks
            code_blocks = re.findall(r'```(?:hcl|terraform)?\s*(.*?)\s*```', terraform_code, re.DOTALL)
            if code_blocks:
                # Combine all code blocks into main.tf
                files["main.tf"] = '\n\n'.join(code_blocks)
            else:
                # Just extract all text as main.tf
                files["main.tf"] = terraform_code.strip()
        
        return files


class TerraformExecutor:
    """
    Executes Terraform commands on the generated code.
    """
    
    def __init__(self):
        """
        Initialize the Terraform executor.
        """
        # Verify terraform is installed
        try:
            subprocess.run(["terraform", "--version"], check=True, capture_output=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("Terraform not found. Please install Terraform and make sure it's in your PATH.")
            raise RuntimeError("Terraform not found")
        
        # Set up Azure credentials
        self.credential = DefaultAzureCredential()
        self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        if not self.subscription_id:
            raise ValueError("Azure subscription ID is required. Please set AZURE_SUBSCRIPTION_ID environment variable.")
        
        # Initialize resource client
        self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)
    
    def _write_terraform_files(self, directory: str, files: Dict[str, str]) -> None:
        """
        Write Terraform files to a directory.
        
        Args:
            directory: The directory to write the files to.
            files: A dictionary mapping file names to their content.
        """
        for file_name, content in files.items():
            file_path = os.path.join(directory, file_name)
            with open(file_path, 'w') as f:
                f.write(content)
    
    def execute_terraform(self, terraform_files: Dict[str, str], operation: str = "apply", auto_approve: bool = False) -> Tuple[bool, str]:
        """
        Execute Terraform operations on the generated code.
        
        Args:
            terraform_files: A dictionary mapping file names to their content.
            operation: The Terraform operation to execute (init, plan, apply, destroy).
            auto_approve: Whether to automatically approve apply/destroy operations.
            
        Returns:
            A tuple containing (success boolean, output/error message).
        """
        valid_operations = ["init", "validate", "plan", "apply", "destroy"]
        if operation not in valid_operations:
            return False, f"Invalid operation: {operation}. Valid operations are {', '.join(valid_operations)}"
        
        # Create a temporary directory for Terraform files
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Using temporary directory: {temp_dir}")
            
            # Write Terraform files to the temporary directory
            self._write_terraform_files(temp_dir, terraform_files)
            
            # Set Azure credentials environment variables for Terraform
            env = os.environ.copy()
            env["ARM_CLIENT_ID"] = os.getenv("AZURE_CLIENT_ID", "")
            env["ARM_CLIENT_SECRET"] = os.getenv("AZURE_CLIENT_SECRET", "")
            env["ARM_SUBSCRIPTION_ID"] = self.subscription_id
            env["ARM_TENANT_ID"] = os.getenv("AZURE_TENANT_ID", "")
            env["TF_LOG"] = "INFO"  # Enable Terraform logging
            
            # Execute Terraform init
            logger.info("Running terraform init")
            init_result = subprocess.run(
                ["terraform", "init"],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True
            )
            
            if init_result.returncode != 0:
                logger.error(f"Terraform init failed: {init_result.stderr}")
                return False, f"Terraform init failed: {init_result.stderr}"
            
            # Execute the requested Terraform operation
            cmd = ["terraform", operation]
            if operation in ["apply", "destroy"] and auto_approve:
                cmd.append("-auto-approve")
            
            logger.info(f"Running terraform {operation}")
            operation_result = subprocess.run(
                cmd,
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True
            )
            
            if operation_result.returncode != 0:
                logger.error(f"Terraform {operation} failed: {operation_result.stderr}")
                return False, f"Terraform {operation} failed: {operation_result.stderr}"
            
            return True, operation_result.stdout


class AzureTerraformAgent:
    """
    Main agent class that coordinates conversation, Terraform generation, and execution.
    Uses Claude AI for model inference.
    """
    
    def __init__(self, 
                 anthropic_api_key: Optional[str] = None,
                 model: Optional[str] = None):
        """
        Initialize the Azure Terraform Agent.
        
        Args:
            anthropic_api_key: Anthropic API key. If None, it will try to get from environment variable.
            model: The Claude model to use. If None, it will use the default.
        """
        self.conversational_agent = ConversationalAgent(
            anthropic_api_key=anthropic_api_key,
            model=model
        )
        self.terraform_generator = TerraformGenerator(
            anthropic_api_key=anthropic_api_key,
            model=model
        )
        self.terraform_executor = TerraformExecutor()
        
        # State to track the current infrastructure spec and Terraform code
        self.current_infrastructure_spec = None
        self.current_terraform_files = None
    
    def process_user_request(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user request for infrastructure changes.
        
        Args:
            user_message: The user's message.
            
        Returns:
            A dictionary containing the response information.
        """
        logger.info(f"Processing user request: {user_message}")

        # Use the conversational agent to interpret the user's request
        response = self.conversational_agent.process_message(user_message)
        
        # Check if we need more information from the user
        if "needs_more_info" in response and response["needs_more_info"]:
            missing_fields = response.get("missing_fields", [])
            
            # Format a message asking for the missing information
            missing_info_message = response.get("message", "I need some additional information to create your Terraform code:")
            
            return {
                "success": False,
                "message": missing_info_message,
                "needs_more_info": True,
                "missing_fields": missing_fields,
                "infrastructure_spec": None,
                "terraform_code": None
            }
        
        if "error" in response:
            return {
                "success": False,
                "message": f"Failed to interpret infrastructure requirements: {response['error']}",
                "infrastructure_spec": None,
                "terraform_code": None
            }
        
        # Store the current infrastructure spec
        self.current_infrastructure_spec = response
        
        # Generate Terraform code based on the infrastructure spec
        terraform_code = self.terraform_generator.generate_terraform_code(response)
        
        # Parse the Terraform code into separate files
        terraform_files = self.terraform_generator.parse_terraform_files(terraform_code)
        
        # Store the current Terraform files
        self.current_terraform_files = terraform_files
        
        # Format the Terraform code for display
        formatted_terraform_code = "\n\n".join([f"# {file_name}\n{content}" for file_name, content in terraform_files.items()])
        
        return {
            "success": True,
            "message": "Successfully generated Terraform code",
            "infrastructure_spec": response,
            "terraform_code": formatted_terraform_code,
            "terraform_files": terraform_files
        }
    
    def validate_terraform(self) -> Dict[str, Any]:
        """
        Validate the current Terraform code.
        
        Returns:
            A dictionary containing the validation result.
        """
        if not self.current_terraform_files:
            return {
                "success": False,
                "message": "No Terraform code has been generated yet"
            }
        
        # Execute Terraform validate
        success, output = self.terraform_executor.execute_terraform(
            self.current_terraform_files,
            operation="validate"
        )
        
        return {
            "success": success,
            "message": output
        }
    
    def plan_terraform(self) -> Dict[str, Any]:
        """
        Generate a Terraform plan for the current code.
        
        Returns:
            A dictionary containing the plan result.
        """
        if not self.current_terraform_files:
            return {
                "success": False,
                "message": "No Terraform code has been generated yet"
            }
        
        # Execute Terraform plan
        success, output = self.terraform_executor.execute_terraform(
            self.current_terraform_files,
            operation="plan"
        )
        
        return {
            "success": success,
            "message": output
        }
    
    def apply_terraform(self, auto_approve: bool = False) -> Dict[str, Any]:
        """
        Apply the current Terraform code.
        
        Args:
            auto_approve: Whether to automatically approve the apply operation.
            
        Returns:
            A dictionary containing the apply result.
        """
        if not self.current_terraform_files:
            return {
                "success": False,
                "message": "No Terraform code has been generated yet"
            }
        
        # Execute Terraform apply
        success, output = self.terraform_executor.execute_terraform(
            self.current_terraform_files,
            operation="apply",
            auto_approve=auto_approve
        )
        
        return {
            "success": success,
            "message": output
        }
    
    def destroy_terraform(self, auto_approve: bool = False) -> Dict[str, Any]:
        """
        Destroy the infrastructure created by the current Terraform code.
        
        Args:
            auto_approve: Whether to automatically approve the destroy operation.
            
        Returns:
            A dictionary containing the destroy result.
        """
        if not self.current_terraform_files:
            return {
                "success": False,
                "message": "No Terraform code has been generated yet"
            }
        
        # Execute Terraform destroy
        success, output = self.terraform_executor.execute_terraform(
            self.current_terraform_files,
            operation="destroy",
            auto_approve=auto_approve
        )
        
        return {
            "success": success,
            "message": output
        }
    
    def get_terraform_code(self) -> Dict[str, Any]:
        """
        Get the current Terraform code.
        
        Returns:
            A dictionary containing the Terraform code.
        """
        if not self.current_terraform_files:
            return {
                "success": False,
                "message": "No Terraform code has been generated yet"
            }
        
        # Format the Terraform code for display
        formatted_terraform_code = "\n\n".join([f"# {file_name}\n{content}" for file_name, content in self.current_terraform_files.items()])
        
        return {
            "success": True,
            "message": "Terraform code retrieved",
            "terraform_code": formatted_terraform_code,
            "terraform_files": self.current_terraform_files
        }
    
    def get_infrastructure_spec(self) -> Dict[str, Any]:
        """
        Get the current infrastructure specification.
        
        Returns:
            A dictionary containing the infrastructure specification.
        """
        if not self.current_infrastructure_spec:
            return {
                "success": False,
                "message": "No infrastructure specification has been generated yet"
            }
        
        return {
            "success": True,
            "message": "Infrastructure specification retrieved",
            "infrastructure_spec": self.current_infrastructure_spec
        }
    
    def clear_conversation_history(self) -> Dict[str, Any]:
        """
        Clear the conversation history.
        
        Returns:
            A dictionary containing the result.
        """
        self.conversational_agent.clear_conversation_history()
        
        return {
            "success": True,
            "message": "Conversation history cleared"
        }