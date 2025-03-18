import os
import json
import logging
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from claude_terraform_agent import AzureTerraformAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# Initialize global variables
agent = None

def setup_agent():
    """
    Set up the Azure Terraform Agent with appropriate credentials.
    """
    global agent
    
    # Check for required environment variables
    required_vars = [
        "AZURE_SUBSCRIPTION_ID",
        "ANTHROPIC_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False, f"Missing required environment variables: {', '.join(missing_vars)}"
    
    # Initialize the agent
    try:
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        
        # Validate Anthropic API key with a simple request
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_api_key)
            
            # Make a simple request to check if the API key is valid
            response = client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}],
                system="You are a helpful assistant."
            )
            
            # If we get here, the API key is valid
            agent = AzureTerraformAgent(
                anthropic_api_key=anthropic_api_key,
                model=model
            )
            return True, f"Agent initialized successfully with Claude model: {model}"
            
        except Exception as e:
            return False, f"Failed to connect to Claude API: {str(e)}"
            
    except Exception as e:
        logger.error(f"Failed to initialize agent: {str(e)}")
        return False, f"Failed to initialize agent: {str(e)}"

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/initialize', methods=['POST'])
def initialize_agent():
    """Initialize the agent and return the status."""
    global agent
    
    success, message = setup_agent()
    
    # Store initialization status in session
    session['agent_initialized'] = success
    
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/process', methods=['POST'])
def process_request():
    """Process a user request and return the result."""
    global agent
    
    # Check if agent is initialized
    if not agent or not session.get('agent_initialized', False):
        success, message = setup_agent()
        if not success:
            return jsonify({
                'success': False,
                'message': "Agent not initialized. " + message
            })
    
    # Get the message from the request
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({
            'success': False,
            'message': "No message provided"
        })
    
    try:
        # Process the user request
        result = agent.process_user_request(user_message)
        
        # Check if the agent needs more information
        if not result.get('success', False) and result.get('needs_more_info', False):
            # Return the request for more info to the frontend
            return jsonify({
                'success': False,
                'message': result['message'],
                'needs_more_info': True,
                'missing_fields': result.get('missing_fields', [])
            })
        
        # Store the result in the session for later use
        session['has_terraform_code'] = result.get('success', False)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error processing request: {str(e)}"
        })

@app.route('/api/terraform/code', methods=['GET'])
def get_terraform_code():
    """Get the current Terraform code."""
    global agent
    
    # Check if agent is initialized
    if not agent or not session.get('agent_initialized', False):
        return jsonify({
            'success': False,
            'message': "Agent not initialized"
        })
    
    # Check if there is Terraform code
    if not session.get('has_terraform_code', False):
        return jsonify({
            'success': False,
            'message': "No Terraform code has been generated yet"
        })
    
    try:
        result = agent.get_terraform_code()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting Terraform code: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting Terraform code: {str(e)}"
        })

@app.route('/api/terraform/validate', methods=['POST'])
def validate_terraform():
    """Validate the current Terraform code."""
    global agent
    
    # Check if agent is initialized
    if not agent or not session.get('agent_initialized', False):
        return jsonify({
            'success': False,
            'message': "Agent not initialized"
        })
    
    # Check if there is Terraform code
    if not session.get('has_terraform_code', False):
        return jsonify({
            'success': False,
            'message': "No Terraform code has been generated yet"
        })
    
    try:
        result = agent.validate_terraform()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error validating Terraform: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error validating Terraform: {str(e)}"
        })

@app.route('/api/terraform/plan', methods=['POST'])
def plan_terraform():
    """Generate a Terraform plan."""
    global agent
    
    # Check if agent is initialized
    if not agent or not session.get('agent_initialized', False):
        return jsonify({
            'success': False,
            'message': "Agent not initialized"
        })
    
    # Check if there is Terraform code
    if not session.get('has_terraform_code', False):
        return jsonify({
            'success': False,
            'message': "No Terraform code has been generated yet"
        })
    
    try:
        result = agent.plan_terraform()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error generating Terraform plan: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error generating Terraform plan: {str(e)}"
        })

@app.route('/api/terraform/apply', methods=['POST'])
def apply_terraform():
    """Apply the current Terraform code."""
    global agent
    
    # Check if agent is initialized
    if not agent or not session.get('agent_initialized', False):
        return jsonify({
            'success': False,
            'message': "Agent not initialized"
        })
    
    # Check if there is Terraform code
    if not session.get('has_terraform_code', False):
        return jsonify({
            'success': False,
            'message': "No Terraform code has been generated yet"
        })
    
    # Get auto-approve option from request
    data = request.json
    auto_approve = data.get('auto_approve', False)
    
    try:
        result = agent.apply_terraform(auto_approve=auto_approve)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error applying Terraform: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error applying Terraform: {str(e)}"
        })

@app.route('/api/terraform/destroy', methods=['POST'])
def destroy_terraform():
    """Destroy the current infrastructure."""
    global agent
    
    # Check if agent is initialized
    if not agent or not session.get('agent_initialized', False):
        return jsonify({
            'success': False,
            'message': "Agent not initialized"
        })
    
    # Check if there is Terraform code
    if not session.get('has_terraform_code', False):
        return jsonify({
            'success': False,
            'message': "No Terraform code has been generated yet"
        })
    
    # Get auto-approve option from request
    data = request.json
    auto_approve = data.get('auto_approve', False)
    
    try:
        result = agent.destroy_terraform(auto_approve=auto_approve)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error destroying infrastructure: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error destroying infrastructure: {str(e)}"
        })

@app.route('/api/clear', methods=['POST'])
def clear_conversation():
    """Clear the conversation history."""
    global agent
    
    # Check if agent is initialized
    if not agent or not session.get('agent_initialized', False):
        return jsonify({
            'success': False,
            'message': "Agent not initialized"
        })
    
    try:
        result = agent.clear_conversation_history()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error clearing conversation: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error clearing conversation: {str(e)}"
        })

if __name__ == '__main__':
    # Set default port or get from environment
    port = int(os.getenv("PORT", 5000))
    
    # Debug mode for development
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    app.run(host='0.0.0.0', port=port, debug=debug)