from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
import os
from datetime import datetime

from . import db
from .models.book import Book, Genre
from .models.license import License
from .models.user import User
from .services.standard_ebooks import StandardEbooksService
from .services.project_gutenberg import ProjectGutenbergService
from .services.internet_archive import InternetArchiveService
from .services.wikisource import WikisourceService
from .utils.license_verifier import LicenseVerifier
from .utils.text_processor import TextProcessor

# Create blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Initialize services
standard_ebooks_service = StandardEbooksService()
project_gutenberg_service = ProjectGutenbergService()
internet_archive_service = InternetArchiveService()
wikisource_service = WikisourceService()
license_verifier = LicenseVerifier()
text_processor = TextProcessor()

# Main routes
@main_bp.route('/')
def index():
    """Home page."""
    # Get some featured books
    recent_books = Book.query.order_by(Book.created_at.desc()).limit(6).all()
    
    return render_template('index.html', 
                          recent_books=recent_books)

@main_bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')

@main_bp.route('/browse')
def browse():
    """Browse books page."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get query parameters
    source = request.args.get('source')
    license_type = request.args.get('license')
    genre = request.args.get('genre')
    
    # Build query
    query = Book.query
    
    if source:
        query = query.filter(Book.source == source)
    
    if license_type:
        query = query.join(Book.license).filter(License.short_name == license_type)
    
    if genre:
        query = query.join(Book.genres).filter(Genre.name == genre)
    
    # Get paginated results
    books = query.order_by(Book.title).paginate(page=page, per_page=per_page)
    
    # Get filter options
    sources = db.session.query(Book.source).distinct().all()
    licenses = License.query.all()
    genres = Genre.query.order_by(Genre.name).all()
    
    return render_template('browse.html', 
                          books=books,
                          sources=sources,
                          licenses=licenses,
                          genres=genres,
                          current_source=source,
                          current_license=license_type,
                          current_genre=genre)

@main_bp.route('/search')
def search():
    """Search books page."""
    query = request.args.get('q', '')
    
    if not query:
        return render_template('search.html', books=[], query='')
    
    # Search in database
    books = Book.query.filter(
        (Book.title.ilike(f'%{query}%')) | 
        (Book.author.ilike(f'%{query}%')) |
        (Book.description.ilike(f'%{query}%'))
    ).all()
    
    return render_template('search.html', books=books, query=query)

@main_bp.route('/book/<int:book_id>')
def book_detail(book_id):
    """Book detail page."""
    book = Book.query.get_or_404(book_id)
    return render_template('book_detail.html', book=book)

@main_bp.route('/book/<int:book_id>/read')
def read_book(book_id):
    """Read book page."""
    book = Book.query.get_or_404(book_id)
    
    # Determine which format to use
    format = request.args.get('format', 'html')
    
    if format == 'html' and book.html_file_path:
        with open(book.html_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template('read.html', book=book, content=content)
    elif format == 'text' and book.text_file_path:
        with open(book.text_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template('read_text.html', book=book, content=content)
    else:
        flash('Requested format not available for this book.', 'warning')
        return redirect(url_for('main.book_detail', book_id=book_id))

@main_bp.route('/book/<int:book_id>/download/<format>')
def download_book(book_id, format):
    """Download book file."""
    book = Book.query.get_or_404(book_id)
    
    if format == 'epub' and book.epub_file_path:
        return send_file(book.epub_file_path, as_attachment=True)
    elif format == 'text' and book.text_file_path:
        return send_file(book.text_file_path, as_attachment=True)
    elif format == 'html' and book.html_file_path:
        return send_file(book.html_file_path, as_attachment=True)
    else:
        flash('Requested format not available for this book.', 'warning')
        return redirect(url_for('main.book_detail', book_id=book_id))

@main_bp.route('/sources')
def sources():
    """Sources page."""
    return render_template('sources.html')

@main_bp.route('/import')
@login_required
def import_page():
    """Import books page."""
    return render_template('import.html')

@main_bp.route('/import/standard-ebooks', methods=['GET', 'POST'])
@login_required
def import_standard_ebooks():
    """Import from Standard Ebooks."""
    if request.method == 'POST':
        url_identifier = request.form.get('url_identifier')
        
        if not url_identifier:
            flash('Please provide a URL identifier.', 'danger')
            return redirect(url_for('main.import_standard_ebooks'))
        
        try:
            # Get book details
            book_details = standard_ebooks_service.get_book_details(url_identifier)
            
            if not book_details:
                flash('Failed to get book details.', 'danger')
                return redirect(url_for('main.import_standard_ebooks'))
            
            # Check if book already exists
            existing_book = Book.query.filter_by(
                source='standard_ebooks',
                source_id=url_identifier
            ).first()
            
            if existing_book:
                flash(f'Book already exists: {existing_book.title}', 'warning')
                return redirect(url_for('main.book_detail', book_id=existing_book.id))
            
            # Download the book
            epub_path = standard_ebooks_service.download_book(url_identifier, format='epub')
            
            if not epub_path:
                flash('Failed to download book.', 'danger')
                return redirect(url_for('main.import_standard_ebooks'))
            
            # Extract text from EPUB
            text_content = text_processor.extract_text_from_epub(epub_path)
            
            # Save text to file
            text_file_path = os.path.join(os.path.dirname(epub_path), f"{os.path.basename(epub_path).split('.')[0]}.txt")
            with open(text_file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            # Create HTML version
            html_content = text_processor.text_to_html(
                text_content, 
                title=book_details.get('title', ''),
                author=book_details.get('author', '')
            )
            
            html_file_path = os.path.join(os.path.dirname(epub_path), f"{os.path.basename(epub_path).split('.')[0]}.html")
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Get or create license
            license = License.query.filter_by(short_name='CC0').first()
            if not license:
                license = License(
                    name='Creative Commons Zero (CC0)',
                    short_name='CC0',
                    description='Creative Commons Zero - Public Domain Dedication. No rights reserved.',
                    url='https://creativecommons.org/publicdomain/zero/1.0/',
                    allows_remix=True,
                    requires_attribution=False,
                    share_alike=False
                )
                db.session.add(license)
                db.session.commit()
            
            # Create book record
            new_book = Book(
                title=book_details.get('title', ''),
                author=book_details.get('author', ''),
                description=book_details.get('description', ''),
                source='standard_ebooks',
                source_id=url_identifier,
                source_url=book_details.get('url', ''),
                license_id=license.id,
                verified=True,
                verification_notes='Standard Ebooks uses CC0 for all their enhancements.',
                verified_by=current_user.id,
                verified_at=datetime.utcnow(),
                epub_file_path=str(epub_path),
                text_file_path=text_file_path,
                html_file_path=html_file_path
            )
            
            # Extract publication year if available
            if 'metadata' in book_details and 'publication_date' in book_details['metadata']:
                pub_date = book_details['metadata']['publication_date']
                year_match = re.search(r'\b(1[0-9]{3}|20[0-2][0-9])\b', pub_date)
                if year_match:
                    new_book.publication_year = int(year_match.group(1))
            
            db.session.add(new_book)
            db.session.commit()
            
            flash(f'Successfully imported: {new_book.title}', 'success')
            return redirect(url_for('main.book_detail', book_id=new_book.id))
            
        except Exception as e:
            flash(f'Error importing book: {str(e)}', 'danger')
            return redirect(url_for('main.import_standard_ebooks'))
    
    # GET request - show form
    return render_template('import_standard_ebooks.html')

@main_bp.route('/import/project-gutenberg', methods=['GET', 'POST'])
@login_required
def import_project_gutenberg():
    """Import from Project Gutenberg."""
    if request.method == 'POST':
        book_id = request.form.get('book_id')
        
        if not book_id:
            flash('Please provide a book ID.', 'danger')
            return redirect(url_for('main.import_project_gutenberg'))
        
        try:
            # Get book details
            book_details = project_gutenberg_service.get_book_details(book_id)
            
            if not book_details:
                flash('Failed to get book details.', 'danger')
                return redirect(url_for('main.import_project_gutenberg'))
            
            # Check if book already exists
            existing_book = Book.query.filter_by(
                source='project_gutenberg',
                source_id=book_id
            ).first()
            
            if existing_book:
                flash(f'Book already exists: {existing_book.title}', 'warning')
                return redirect(url_for('main.book_detail', book_id=existing_book.id))
            
            # Download the book
            epub_path = project_gutenberg_service.download_book(book_id, format='epub')
            
            if not epub_path:
                # Try text format if EPUB is not available
                text_path = project_gutenberg_service.download_book(book_id, format='txt')
                
                if not text_path:
                    flash('Failed to download book.', 'danger')
                    return redirect(url_for('main.import_project_gutenberg'))
                
                # Read text content
                with open(text_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                
                # Remove PG branding
                text_content = project_gutenberg_service.remove_pg_branding(text_content)
                
                # Save cleaned text
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                
                # Create HTML version
                html_content = text_processor.text_to_html(
                    text_content, 
                    title=book_details.get('title', ''),
                    author=book_details.get('author', '')
                )
                
                html_file_path = os.path.join(os.path.dirname(text_path), f"{os.path.basename(text_path).split('.')[0]}.html")
                with open(html_file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                epub_path = None
            else:
                # Extract text from EPUB
                text_content = text_processor.extract_text_from_epub(epub_path)
                
                # Remove PG branding
                text_content = project_gutenberg_service.remove_pg_branding(text_content)
                
                # Save cleaned text
                text_file_path = os.path.join(os.path.dirname(epub_path), f"{os.path.basename(epub_path).split('.')[0]}.txt")
                with open(text_file_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                
                # Create HTML version
                html_content = text_processor.text_to_html(
                    text_content, 
                    title=book_details.get('title', ''),
                    author=book_details.get('author', '')
                )
                
                html_file_path = os.path.join(os.path.dirname(epub_path), f"{os.path.basename(epub_path).split('.')[0]}.html")
                with open(html_file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            
            # Get or create license
            license = License.query.filter_by(short_name='PD-US').first()
            if not license:
                license = License(
                    name='Public Domain (US)',
                    short_name='PD-US',
                    description='Works in the US public domain (published before 1929). No copyright restrictions in the US.',
                    url='https://en.wikipedia.org/wiki/Public_domain_in_the_United_States',
                    allows_remix=True,
                    requires_attribution=False,
                    share_alike=False
                )
                db.session.add(license)
                db.session.commit()
            
            # Create book record
            new_book = Book(
                title=book_details.get('title', ''),
                author=book_details.get('author', ''),
                description=book_details.get('bibrec', {}).get('subject', ''),
                source='project_gutenberg',
                source_id=book_id,
                source_url=book_details.get('url', ''),
                license_id=license.id,
                verified=True,
                verification_notes='Project Gutenberg text with PG branding removed.',
                verified_by=current_user.id,
                verified_at=datetime.utcnow(),
                epub_file_path=str(epub_path) if epub_path else None,
                text_file_path=text_file_path if 'text_file_path' in locals() else text_path,
                html_file_path=html_file_path
            )
            
            # Extract publication year if available
            if 'bibrec' in book_details and 'release_date' in book_details['bibrec']:
                release_date = book_details['bibrec']['release_date']
                year_match = re.search(r'\b(1[0-9]{3}|20[0-2][0-9])\b', release_date)
                if year_match:
                    new_book.publication_year = int(year_match.group(1))
            
            db.session.add(new_book)
            db.session.commit()
            
            flash(f'Successfully imported: {new_book.title}', 'success')
            return redirect(url_for('main.book_detail', book_id=new_book.id))
            
        except Exception as e:
            flash(f'Error importing book: {str(e)}', 'danger')
            return redirect(url_for('main.import_project_gutenberg'))
    
    # GET request - show form
    return render_template('import_project_gutenberg.html')

# Authentication routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return render_template('auth/register.html')
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            display_name=username
        )
        new_user.set_password(password)
        
        # First user is admin
        if User.query.count() == 0:
            new_user.role = 'admin'
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile."""
    return render_template('auth/profile.html')

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile."""
    if request.method == 'POST':
        display_name = request.form.get('display_name')
        bio = request.form.get('bio')
        
        current_user.display_name = display_name
        current_user.bio = bio
        
        db.session.commit()
        
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/edit_profile.html')

# API routes
@api_bp.route('/books')
def api_books():
    """API endpoint for books."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    books = Book.query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'books': [book.to_dict() for book in books.items],
        'total': books.total,
        'pages': books.pages,
        'page': books.page
    })

@api_bp.route('/books/<int:book_id>')
def api_book_detail(book_id):
    """API endpoint for book details."""
    book = Book.query.get_or_404(book_id)
    return jsonify(book.to_dict())

@api_bp.route('/search')
def api_search():
    """API endpoint for search."""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'books': []})
    
    books = Book.query.filter(
        (Book.title.ilike(f'%{query}%')) | 
        (Book.author.ilike(f'%{query}%')) |
        (Book.description.ilike(f'%{query}%'))
    ).all()
    
    return jsonify({
        'books': [book.to_dict() for book in books]
    })
