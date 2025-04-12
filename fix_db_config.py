"""
Database configuration fix script for Remixable Fiction Library.
This script directly modifies the database configuration to use an absolute path.
"""

import os
import sys
import logging
import sqlite3

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_db_config():
    """Fix the database configuration to use an absolute path."""
    try:
        # Get absolute paths
        project_root = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(project_root, 'data')
        db_path = os.path.join(data_dir, 'library.db')
        
        logger.info(f"Project root: {project_root}")
        logger.info(f"Data directory: {data_dir}")
        logger.info(f"Database path: {db_path}")
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Ensured data directory exists: {data_dir}")
        
        # Create an empty database file
        try:
            logger.info(f"Creating database file: {db_path}")
            conn = sqlite3.connect(db_path)
            conn.close()
            logger.info("Database file created successfully")
        except Exception as e:
            logger.error(f"Error creating database file: {str(e)}")
            return False
        
        # Set permissions on the database file
        try:
            os.chmod(db_path, 0o666)  # rw-rw-rw-
            logger.info("Set permissions on database file")
        except Exception as e:
            logger.error(f"Error setting permissions: {str(e)}")
            
        # Create a .env file with the absolute database path
        env_path = os.path.join(project_root, '.env')
        
        # Check if .env exists and read its contents
        env_contents = {}
        if os.path.exists(env_path):
            logger.info(f"Reading existing .env file: {env_path}")
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        env_contents[key] = value
        
        # Update the DATABASE_URI with absolute path
        env_contents['DATABASE_URI'] = f"sqlite:////{db_path}"
        
        # Write the updated .env file
        logger.info(f"Writing updated .env file with absolute database path")
        with open(env_path, 'w') as f:
            for key, value in env_contents.items():
                f.write(f"{key}={value}\n")
        
        logger.info(f"Database configuration fixed. New URI: sqlite:////{db_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing database configuration: {str(e)}")
        return False

if __name__ == "__main__":
    success = fix_db_config()
    if success:
        print("\n✅ Database configuration fixed successfully!")
        print("You can now run the application with: python run.py")
        sys.exit(0)
    else:
        print("\n❌ Failed to fix database configuration!")
        sys.exit(1)
