from datetime import datetime
from .. import db

# Association table for book-genre relationship
book_genre = db.Table('book_genre',
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'), primary_key=True)
)

class Book(db.Model):
    """Model for books in the library."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    publication_year = db.Column(db.Integer)
    language = db.Column(db.String(50), default='en')
    description = db.Column(db.Text)
    
    # Source information
    source = db.Column(db.String(50), nullable=False)  # 'standard_ebooks', 'project_gutenberg', 'internet_archive', 'wikisource'
    source_id = db.Column(db.String(100))  # ID from the original source
    source_url = db.Column(db.String(255))  # URL to the original source
    
    # License information
    license_id = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=False)
    license = db.relationship('License', backref='books')
    
    # Verification status
    verified = db.Column(db.Boolean, default=False)
    verification_notes = db.Column(db.Text)
    verified_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    verified_at = db.Column(db.DateTime)
    
    # File information
    text_file_path = db.Column(db.String(255))
    epub_file_path = db.Column(db.String(255))
    html_file_path = db.Column(db.String(255))
    
    # Metadata
    cover_image_path = db.Column(db.String(255))
    page_count = db.Column(db.Integer)
    word_count = db.Column(db.Integer)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    genres = db.relationship('Genre', secondary=book_genre, backref='books')
    
    def __repr__(self):
        return f'<Book {self.title} by {self.author}>'
    
    def to_dict(self):
        """Convert book to dictionary for API responses."""
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'publication_year': self.publication_year,
            'language': self.language,
            'description': self.description,
            'source': self.source,
            'source_url': self.source_url,
            'license': self.license.name if self.license else None,
            'verified': self.verified,
            'genres': [genre.name for genre in self.genres],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Genre(db.Model):
    """Model for book genres."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Genre {self.name}>'
