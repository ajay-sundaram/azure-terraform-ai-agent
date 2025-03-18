#!/usr/bin/env python
import os
from dotenv import load_dotenv
from claude_terraform_web import app

# Load environment variables
load_dotenv()

if __name__ == '__main__':
    # Set default port or get from environment
    port = int(os.getenv("PORT", 5000))
    
    # Debug mode for development
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    app.run(host='0.0.0.0', port=port, debug=debug)
