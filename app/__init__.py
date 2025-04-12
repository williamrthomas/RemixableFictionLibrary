from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize SQLAlchemy
db = SQLAlchemy()

# Initialize LoginManager
login_manager = LoginManager()

def create_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    
    # Configure the app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-development')
    
    # Get the absolute path to the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logger.info(f"Project root: {project_root}")
    
    # Ensure data directory exists with absolute path
    data_dir = os.path.join(project_root, 'data')
    os.makedirs(data_dir, exist_ok=True)
    logger.info(f"Ensured data directory exists: {data_dir}")
    
    # Set database path with absolute path - using 4 slashes for absolute path
    db_path = os.path.join(data_dir, 'library.db')
    
    # FORCE absolute path with four slashes for SQLite, bypassing environment variables
    db_uri = f"sqlite:////{db_path}"
    logger.info(f"Forcing absolute database URI: {db_uri}")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Log the database URI for debugging
    logger.info(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    logger.info(f"Database file path: {db_path}")
    
    # Initialize plugins
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    with app.app_context():
        # Import parts of our application
        from .models import book, license, user
        from .services import standard_ebooks, project_gutenberg, internet_archive, wikisource
        
        # Import user loader
        from .models.user import User
        
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
        
        # Register blueprints
        from .blueprints.main import main_bp
        from .blueprints.auth import auth_bp
        from .blueprints.api import api_bp
        
        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(api_bp)
        
        try:
            # Create database tables
            logger.info("Attempting to create database tables...")
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            # Continue execution to allow the application to start even if DB fails
            # This allows the demo mode to work without a database
        
        return app
