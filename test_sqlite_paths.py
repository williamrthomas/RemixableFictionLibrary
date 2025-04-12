"""
SQLite Path Resolution Test

This script tests SQLite database connections with different path formats
to diagnose database initialization issues in the Remixable Fiction Library.
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_sqlite_connections():
    """Test SQLite connections with different path formats."""
    
    # Get current working directory and project root
    cwd = os.getcwd()
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    logger.info(f"Current working directory: {cwd}")
    logger.info(f"Project root directory: {project_root}")
    
    # Define test paths
    test_paths = [
        # Test 1: Relative path from current directory
        {
            "name": "Relative path (current dir)",
            "path": "data/test_relative.db",
            "description": "Relative path from current working directory"
        },
        # Test 2: Relative path with explicit directory creation
        {
            "name": "Relative path with dir creation",
            "path": "data/test_explicit.db",
            "create_dir": True,
            "description": "Relative path with explicit directory creation"
        },
        # Test 3: Absolute path
        {
            "name": "Absolute path",
            "path": os.path.join(project_root, "data", "test_absolute.db"),
            "description": "Absolute path to database file"
        },
        # Test 4: Path in /tmp directory (should always be writable)
        {
            "name": "Temp directory path",
            "path": "/tmp/test_sqlite.db",
            "description": "Path in system temp directory"
        }
    ]
    
    results = []
    
    # Run tests for each path
    for test in test_paths:
        logger.info(f"\n=== Testing: {test['name']} ===")
        logger.info(f"Path: {test['path']}")
        logger.info(f"Description: {test['description']}")
        
        # Create directory if specified
        if test.get("create_dir", False):
            dir_path = os.path.dirname(test['path'])
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
        
        # Test connection
        success = False
        error_msg = None
        
        try:
            # Try to create and connect to the database
            logger.info(f"Attempting to connect to: {test['path']}")
            conn = sqlite3.connect(test['path'])
            cursor = conn.cursor()
            
            # Create a simple test table
            cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
            
            # Insert a test record
            cursor.execute("INSERT INTO test (name) VALUES (?)", (f"Test for {test['name']}",))
            
            # Commit changes
            conn.commit()
            
            # Verify we can read the data
            cursor.execute("SELECT * FROM test")
            result = cursor.fetchone()
            logger.info(f"Read data from database: {result}")
            
            # Close connection
            conn.close()
            
            success = True
            logger.info(f"✅ Successfully created and accessed database at: {test['path']}")
            
            # Check if file exists
            if os.path.exists(test['path']):
                file_size = os.path.getsize(test['path'])
                file_perms = oct(os.stat(test['path']).st_mode)[-3:]
                logger.info(f"File exists: {test['path']} (Size: {file_size} bytes, Permissions: {file_perms})")
            else:
                logger.warning(f"File does not exist despite successful connection: {test['path']}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error with database path {test['path']}: {error_msg}")
        
        # Record result
        results.append({
            "name": test['name'],
            "path": test['path'],
            "success": success,
            "error": error_msg
        })
    
    # Print summary
    logger.info("\n=== Test Results Summary ===")
    for result in results:
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        logger.info(f"{status} - {result['name']}: {result['path']}")
        if not result['success']:
            logger.info(f"  Error: {result['error']}")
    
    # Suggest solution based on results
    logger.info("\n=== Recommendation ===")
    if any(r['success'] for r in results):
        successful_paths = [r for r in results if r['success']]
        logger.info("Based on the test results, the following paths work for SQLite:")
        for path in successful_paths:
            logger.info(f"- {path['name']}: {path['path']}")
        
        # Recommend the absolute path if it worked
        abs_path_result = next((r for r in results if r['name'] == "Absolute path"), None)
        if abs_path_result and abs_path_result['success']:
            logger.info("\nRecommendation: Use an absolute path in your SQLAlchemy configuration:")
            logger.info(f"app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////{abs_path_result['path']}'")
            logger.info("Note the four slashes for absolute paths in SQLAlchemy.")
    else:
        logger.info("All connection attempts failed. This might indicate a system-level SQLite issue.")
        logger.info("Check if SQLite is properly installed and if the user has write permissions.")

if __name__ == "__main__":
    test_sqlite_connections()
