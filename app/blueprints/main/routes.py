"""
Main routes for Remixable Fiction Library.
This module contains the routes for the main blueprint.
"""

from flask import render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import current_user
import os
import re
from datetime import datetime
import uuid

from . import main_bp
from app import db
from app.models.book import Book, Genre
from app.models.license import License
from app.services.standard_ebooks import StandardEbooksService
from app.services.project_gutenberg import ProjectGutenbergService
from app.services.internet_archive import InternetArchiveService
from app.services.wikisource import WikisourceService
from app.utils.license_verifier import LicenseVerifier
from app.utils.text_processor import TextProcessor

# Initialize services
standard_ebooks_service = StandardEbooksService()
project_gutenberg_service = ProjectGutenbergService()
internet_archive_service = InternetArchiveService()
wikisource_service = WikisourceService()
license_verifier = LicenseVerifier()
text_processor = TextProcessor()

# Store import requests in memory (would be in database in production)
import_requests = []

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
def import_page():
    """Import books page - now public."""
    return render_template('import.html', is_authenticated=current_user.is_authenticated)

@main_bp.route('/import/request', methods=['GET', 'POST'])
def import_request():
    """Public import request form."""
    if request.method == 'POST':
        source = request.form.get('source')
        identifier = request.form.get('identifier')
        title = request.form.get('title')
        author = request.form.get('author')
        notes = request.form.get('notes')
        email = request.form.get('email', '')
        
        if not source or not identifier or not title:
            flash('Please provide the source, identifier, and title.', 'danger')
            return redirect(url_for('main.import_request'))
        
        # Create a unique ID for the request
        request_id = str(uuid.uuid4())
        
        # Store the request
        import_requests.append({
            'id': request_id,
            'source': source,
            'identifier': identifier,
            'title': title,
            'author': author,
            'notes': notes,
            'email': email,
            'status': 'pending',
            'created_at': datetime.utcnow()
        })
        
        flash('Your import request has been submitted. Thank you for contributing to the library!', 'success')
        return redirect(url_for('main.import_status', request_id=request_id))
    
    return render_template('import_request.html')

@main_bp.route('/import/status/<request_id>')
def import_status(request_id):
    """Check status of an import request."""
    # Find the request
    request_data = next((req for req in import_requests if req['id'] == request_id), None)
    
    if not request_data:
        flash('Import request not found.', 'danger')
        return redirect(url_for('main.import_page'))
    
    return render_template('import_status.html', request=request_data)

@main_bp.route('/import/list')
def import_list():
    """List all import requests - visible to everyone."""
    # In a real implementation, this would have pagination
    return render_template('import_list.html', requests=import_requests)

# Admin-only import functionality (still accessible to admins)
@main_bp.route('/import/standard-ebooks', methods=['GET', 'POST'])
def import_standard_ebooks():
    """Import from Standard Ebooks."""
    # Check if user is authenticated and is admin
    if not current_user.is_authenticated:
        flash('You need to be logged in as an admin to import books directly.', 'warning')
        return redirect(url_for('main.import_request'))
    
    if not current_user.is_admin():
        flash('Only administrators can import books directly.', 'warning')
        return redirect(url_for('main.import_request'))
    
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
def import_project_gutenberg():
    """Import from Project Gutenberg."""
    # Check if user is authenticated and is admin
    if not current_user.is_authenticated:
        flash('You need to be logged in as an admin to import books directly.', 'warning')
        return redirect(url_for('main.import_request'))
    
    if not current_user.is_admin():
        flash('Only administrators can import books directly.', 'warning')
        return redirect(url_for('main.import_request'))
    
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

# Add public API endpoints
@main_bp.route('/api/public/books')
def public_books_api():
    """Public API endpoint for books."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    books = Book.query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'books': [
            {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'source': book.source,
                'license': book.license.short_name if book.license else None,
                'url': url_for('main.book_detail', book_id=book.id, _external=True)
            } for book in books.items
        ],
        'total': books.total,
        'pages': books.pages,
        'page': books.page
    })
