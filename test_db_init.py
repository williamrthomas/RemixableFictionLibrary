"""
Test script for database initialization.
This script tests the database initialization process to ensure it works correctly.
"""

import os
import sys
import sqlite3
import logging
import shutil

def test_db_initialization():
    """Test the database initialization process."""
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Define paths using absolute paths
    project_root = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(project_root, 'data')
    db_path = os.path.join(data_dir, 'library.db')
    
    logger.info(f"Project root: {project_root}")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Database path: {db_path}")
    
    # Test 1: Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)
    
    # Test 2: Remove database file if it exists
    if os.path.exists(db_path):
        logger.info("Removing existing database file for testing...")
        try:
            os.remove(db_path)
        except PermissionError:
            logger.error("Permission error when trying to remove the database file.")
            logger.info("Attempting to fix permissions...")
            # Try to change permissions
            try:
                os.chmod(db_path, 0o666)  # Read/write for everyone
                os.remove(db_path)
                logger.info("Successfully removed database file after fixing permissions.")
            except Exception as e:
                logger.error(f"Could not fix permissions: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Error removing database file: {str(e)}")
            return False
    
    # Import here to ensure environment is set up correctly
    from app.init_db import init_db
    
    # Test 3: Initialize database
    logger.info("Initializing database...")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Error during database initialization: {str(e)}")
        return False
    
    # Test 4: Verify database file exists
    if not os.path.exists(db_path):
        logger.error("Database file was not created!")
        return False
    
    logger.info("Database file was created successfully.")
    
    # Test 5: Verify database tables were created
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        expected_tables = ['user', 'license', 'genre', 'book']
        for table in expected_tables:
            if table not in table_names:
                logger.error(f"Table '{table}' was not created!")
                conn.close()
                return False
        
        logger.info(f"Found tables: {', '.join(table_names)}")
        
        # Check for data in license table
        cursor.execute("SELECT COUNT(*) FROM license;")
        license_count = cursor.fetchone()[0]
        logger.info(f"License count: {license_count}")
        
        # Check for data in genre table
        cursor.execute("SELECT COUNT(*) FROM genre;")
        genre_count = cursor.fetchone()[0]
        logger.info(f"Genre count: {genre_count}")
        
        # Check for admin user
        cursor.execute("SELECT COUNT(*) FROM user WHERE username='admin';")
        admin_count = cursor.fetchone()[0]
        logger.info(f"Admin user count: {admin_count}")
        
        conn.close()
        
        if license_count < 1 or genre_count < 1 or admin_count < 1:
            logger.error("Database was not properly populated with initial data!")
            return False
        
        logger.info("Database tables and data were created successfully.")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        return False

if __name__ == "__main__":
    success = test_db_initialization()
    if success:
        print("\n✅ Database initialization test passed!")
        sys.exit(0)
    else:
        print("\n❌ Database initialization test failed!")
        sys.exit(1)
