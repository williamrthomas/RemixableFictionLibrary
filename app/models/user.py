from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .. import db, login_manager

class User(UserMixin, db.Model):
    """Model for user accounts."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    # User profile
    display_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    
    # User role
    role = db.Column(db.String(20), default='user')  # 'user', 'editor', 'admin'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    verified_books = db.relationship('Book', backref='verifier', foreign_keys='Book.verified_by')
    
    def set_password(self, password):
        """Set password hash for user."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is an admin."""
        return self.role == 'admin'
    
    def is_editor(self):
        """Check if user is an editor."""
        return self.role in ['editor', 'admin']
    
    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))
