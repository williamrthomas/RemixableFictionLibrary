"""
Database initialization script for Remixable Fiction Library.
This script populates the database with initial data like license types and genres.
"""

from app import create_app, db
from app.models.license import License
from app.models.book import Genre
from app.models.user import User
from werkzeug.security import generate_password_hash
from datetime import datetime
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database with required data."""
    try:
        # Create app instance
        logger.info("Creating Flask application instance...")
        app = create_app()
        
        # Get the absolute path to the database file from the app config
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        logger.info(f"Database URI from config: {db_uri}")
        
        # Extract the file path from the URI
        if db_uri.startswith('sqlite:////'):  # Four slashes for absolute path
            db_path = db_uri.replace('sqlite:////', '')
            logger.info(f"Using absolute database path: {db_path}")
        elif db_uri.startswith('sqlite:///'):  # Three slashes for relative path
            db_path = db_uri.replace('sqlite:///', '')
            logger.info(f"Using relative database path: {db_path}")
            # Convert to absolute path for logging
            abs_path = os.path.abspath(db_path)
            logger.info(f"Absolute path resolution: {abs_path}")
        
        with app.app_context():
            try:
                logger.info("Creating database tables...")
                db.create_all()
                
                # Create license types if they don't exist
                logger.info("Creating license types...")
                licenses = [
                    {
                        'name': 'Public Domain (US)',
                        'short_name': 'PD-US',
                        'description': 'Works in the US public domain (published before 1929). No copyright restrictions in the US.',
                        'url': 'https://en.wikipedia.org/wiki/Public_domain_in_the_United_States',
                        'allows_remix': True,
                        'requires_attribution': False,
                        'share_alike': False
                    },
                    {
                        'name': 'Creative Commons Zero (CC0)',
                        'short_name': 'CC0',
                        'description': 'Creative Commons Zero - Public Domain Dedication. No rights reserved.',
                        'url': 'https://creativecommons.org/publicdomain/zero/1.0/',
                        'allows_remix': True,
                        'requires_attribution': False,
                        'share_alike': False
                    },
                    {
                        'name': 'Creative Commons Attribution (CC BY)',
                        'short_name': 'CC-BY',
                        'description': 'Creative Commons Attribution. Allows remix with attribution.',
                        'url': 'https://creativecommons.org/licenses/by/4.0/',
                        'allows_remix': True,
                        'requires_attribution': True,
                        'share_alike': False
                    },
                    {
                        'name': 'Creative Commons Attribution-ShareAlike (CC BY-SA)',
                        'short_name': 'CC-BY-SA',
                        'description': 'Creative Commons Attribution-ShareAlike. Allows remix with attribution, derivatives must use same license.',
                        'url': 'https://creativecommons.org/licenses/by-sa/4.0/',
                        'allows_remix': True,
                        'requires_attribution': True,
                        'share_alike': True
                    },
                    {
                        'name': 'Project Gutenberg License',
                        'short_name': 'PG',
                        'description': 'Project Gutenberg License. US public domain text with trademark restrictions.',
                        'url': 'https://www.gutenberg.org/policy/license.html',
                        'allows_remix': True,
                        'requires_attribution': False,
                        'share_alike': False
                    }
                ]
                
                for license_data in licenses:
                    existing = License.query.filter_by(short_name=license_data['short_name']).first()
                    if not existing:
                        new_license = License(**license_data)
                        db.session.add(new_license)
                
                # Create genres if they don't exist
                logger.info("Creating genres...")
                genres = [
                    "Adventure",
                    "Classic",
                    "Drama",
                    "Fantasy",
                    "Fiction",
                    "Historical Fiction",
                    "Horror",
                    "Humor",
                    "Mystery",
                    "Philosophy",
                    "Poetry",
                    "Romance",
                    "Science Fiction",
                    "Short Stories",
                    "Thriller",
                    "Tragedy",
                    "Western"
                ]
                
                for genre_name in genres:
                    existing = Genre.query.filter_by(name=genre_name).first()
                    if not existing:
                        new_genre = Genre(name=genre_name)
                        db.session.add(new_genre)
                
                # Create admin user if no users exist
                if User.query.count() == 0:
                    logger.info("Creating admin user...")
                    admin_user = User(
                        username="admin",
                        email="admin@example.com",
                        display_name="Administrator",
                        role="admin",
                        created_at=datetime.utcnow()
                    )
                    admin_user.password_hash = generate_password_hash("admin123")  # Default password, should be changed
                    db.session.add(admin_user)
                
                db.session.commit()
                logger.info("Database initialization complete!")
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Database initialization failed: {str(e)}")
                raise
                
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
