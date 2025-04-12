"""
Run script for Remixable Fiction Library.
This script initializes the database and starts the web server.
"""

from app import create_app
from app.init_db import init_db

if __name__ == "__main__":
    # Initialize the database
    init_db()
    
    # Create and run the app
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5002)  # Changed port to 5002
