"""
Database fix script for Remixable Fiction Library.
This script creates the necessary directory structure and database file with proper permissions.
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

def fix_database():
    """Create the database file and directory structure with proper permissions."""
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Get absolute paths
    project_root = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(project_root, 'data')
    db_path = os.path.join(data_dir, 'library.db')
    
    logger.info(f"Project root: {project_root}")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Database path: {db_path}")
    
    try:
        # Ensure data directory exists with proper permissions
        os.makedirs(data_dir, exist_ok=True)
        os.chmod(data_dir, 0o755)  # rwxr-xr-x
        logger.info(f"Ensured data directory exists with proper permissions: {data_dir}")
        
        # Remove existing database file if it exists
        if os.path.exists(db_path):
            logger.info("Removing existing database file...")
            try:
                os.remove(db_path)
            except PermissionError:
                logger.error("Permission error when trying to remove the database file.")
                logger.info("Attempting to fix permissions...")
                try:
                    os.chmod(db_path, 0o666)  # rw-rw-rw-
                    os.remove(db_path)
                except Exception as e:
                    logger.error(f"Could not fix permissions: {str(e)}")
                    return False
        
        # Create an empty SQLite database file with proper permissions
        logger.info("Creating new database file...")
        conn = sqlite3.connect(db_path)
        conn.close()
        
        # Set permissions on the database file
        os.chmod(db_path, 0o666)  # rw-rw-rw-
        logger.info(f"Set permissions on database file: {db_path}")
        
        # Verify the database file exists and is writable
        if os.path.exists(db_path) and os.access(db_path, os.W_OK):
            logger.info("Database file created successfully and is writable.")
            return True
        else:
            logger.error("Database file exists but is not writable!")
            return False
            
    except Exception as e:
        logger.error(f"Error fixing database: {str(e)}")
        return False

if __name__ == "__main__":
    success = fix_database()
    if success:
        print("\n✅ Database fix completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Database fix failed!")
        sys.exit(1)
