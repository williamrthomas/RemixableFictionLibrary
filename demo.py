"""
Demo application for Remixable Fiction Library.
This is a simplified version without database dependencies for preview purposes.
"""

from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash
import os
from datetime import datetime

# Create Flask application
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')
app.secret_key = 'demo-secret-key'

# Create blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Sample data for demonstration
class Book:
    def __init__(self, id, title, author, description, source, license_name, license_description, license_url):
        self.id = id
        self.title = title
        self.author = author
        self.description = description
        self.source = source
        self.source_url = f"https://example.com/book/{id}"
        self.license = type('obj', (object,), {
            'name': license_name,
            'description': license_description,
            'url': license_url,
            'requires_attribution': 'Attribution' in license_name,
            'share_alike': 'ShareAlike' in license_name
        })
        self.verified = True
        self.verification_notes = "Verified for demonstration purposes."
        self.created_at = datetime.now()
        self.verified_at = datetime.now()
        self.genres = []
        self.epub_file_path = f"/path/to/epub/{id}.epub"
        self.text_file_path = f"/path/to/text/{id}.txt"
        self.html_file_path = f"/path/to/html/{id}.html"
        self.cover_image_path = None
        self.publication_year = 1900 + id
        self.language = "en"

# Create sample books
books = [
    Book(1, "Pride and Prejudice", "Jane Austen", 
         "Pride and Prejudice is a romantic novel by Jane Austen, published in 1813. The story follows the main character Elizabeth Bennet as she deals with issues of manners, upbringing, morality, education, and marriage in the society of the landed gentry of early 19th-century England.",
         "standard_ebooks", "Creative Commons Zero (CC0)", 
         "Creative Commons Zero - Public Domain Dedication. No rights reserved.", 
         "https://creativecommons.org/publicdomain/zero/1.0/"),
    Book(2, "Frankenstein", "Mary Shelley", 
         "Frankenstein; or, The Modern Prometheus is an 1818 novel written by English author Mary Shelley. Frankenstein tells the story of Victor Frankenstein, a young scientist who creates a sapient creature in an unorthodox scientific experiment.",
         "project_gutenberg", "Public Domain (US)", 
         "Works in the US public domain (published before 1929). No copyright restrictions in the US.", 
         "https://en.wikipedia.org/wiki/Public_domain_in_the_United_States"),
    Book(3, "The Time Machine", "H.G. Wells", 
         "The Time Machine is a science fiction novella by H. G. Wells, published in 1895. The work is generally credited with the popularization of the concept of time travel by using a vehicle or device to travel purposely and selectively forward or backward through time.",
         "internet_archive", "Public Domain (US)", 
         "Works in the US public domain (published before 1929). No copyright restrictions in the US.", 
         "https://en.wikipedia.org/wiki/Public_domain_in_the_United_States"),
    Book(4, "The Yellow Wallpaper", "Charlotte Perkins Gilman", 
         "The Yellow Wallpaper is a short story by American writer Charlotte Perkins Gilman, first published in January 1892 in The New England Magazine. It is regarded as an important early work of American feminist literature.",
         "wikisource", "Creative Commons Attribution-ShareAlike (CC BY-SA)", 
         "Creative Commons Attribution-ShareAlike. Allows remix with attribution, derivatives must use same license.", 
         "https://creativecommons.org/licenses/by-sa/4.0/"),
    Book(5, "A Princess of Mars", "Edgar Rice Burroughs", 
         "A Princess of Mars is a science fantasy novel by American writer Edgar Rice Burroughs, the first of his Barsoom series. It was first serialized in the pulp magazine All-Story Magazine from February–July, 1912.",
         "standard_ebooks", "Creative Commons Zero (CC0)", 
         "Creative Commons Zero - Public Domain Dedication. No rights reserved.", 
         "https://creativecommons.org/publicdomain/zero/1.0/"),
    Book(6, "The Adventures of Sherlock Holmes", "Arthur Conan Doyle", 
         "The Adventures of Sherlock Holmes is a collection of twelve short stories by Arthur Conan Doyle, first published on 14 October 1892. It contains the earliest short stories featuring the consulting detective Sherlock Holmes.",
         "project_gutenberg", "Public Domain (US)", 
         "Works in the US public domain (published before 1929). No copyright restrictions in the US.", 
         "https://en.wikipedia.org/wiki/Public_domain_in_the_United_States"),
]

# Add genres to books
books[0].genres = [type('obj', (object,), {'name': 'Classic'}), type('obj', (object,), {'name': 'Romance'})]
books[1].genres = [type('obj', (object,), {'name': 'Horror'}), type('obj', (object,), {'name': 'Science Fiction'})]
books[2].genres = [type('obj', (object,), {'name': 'Science Fiction'})]
books[3].genres = [type('obj', (object,), {'name': 'Short Stories'})]
books[4].genres = [type('obj', (object,), {'name': 'Adventure'}), type('obj', (object,), {'name': 'Science Fiction'})]
books[5].genres = [type('obj', (object,), {'name': 'Mystery'})]

# Main routes
@main_bp.route('/')
def index():
    """Home page."""
    recent_books = books[:6]
    return render_template('index.html', recent_books=recent_books)

@main_bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')

@main_bp.route('/browse')
def browse():
    """Browse books page."""
    page = request.args.get('page', 1, type=int)
    
    # Get query parameters
    source = request.args.get('source')
    license_type = request.args.get('license')
    genre = request.args.get('genre')
    
    # Filter books (simple implementation for demo)
    filtered_books = books
    if source:
        filtered_books = [b for b in filtered_books if b.source == source]
    
    # Create a simple pagination object
    class Pagination:
        def __init__(self, items, page, per_page=20):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = len(items)
            self.pages = (self.total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1
            self.next_num = page + 1
        
        def iter_pages(self, left_edge=1, right_edge=1, left_current=2, right_current=2):
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and num < self.page + right_current) or \
                   num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num
    
    # Create pagination
    pagination = Pagination(filtered_books, page)
    
    # Get sources, licenses, and genres for filters
    sources = [('standard_ebooks',), ('project_gutenberg',), ('internet_archive',), ('wikisource',)]
    licenses = [
        type('obj', (object,), {'name': 'Public Domain (US)', 'short_name': 'PD-US'}),
        type('obj', (object,), {'name': 'Creative Commons Zero (CC0)', 'short_name': 'CC0'}),
        type('obj', (object,), {'name': 'Creative Commons Attribution (CC BY)', 'short_name': 'CC-BY'}),
        type('obj', (object,), {'name': 'Creative Commons Attribution-ShareAlike (CC BY-SA)', 'short_name': 'CC-BY-SA'})
    ]
    genres = [
        type('obj', (object,), {'name': 'Adventure'}),
        type('obj', (object,), {'name': 'Classic'}),
        type('obj', (object,), {'name': 'Horror'}),
        type('obj', (object,), {'name': 'Mystery'}),
        type('obj', (object,), {'name': 'Romance'}),
        type('obj', (object,), {'name': 'Science Fiction'}),
        type('obj', (object,), {'name': 'Short Stories'})
    ]
    
    return render_template('browse.html', 
                          books=pagination,
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
    
    # Simple search implementation for demo
    results = []
    for book in books:
        if (query.lower() in book.title.lower() or 
            query.lower() in book.author.lower() or 
            query.lower() in book.description.lower()):
            results.append(book)
    
    return render_template('search.html', books=results, query=query)

@main_bp.route('/book/<int:book_id>')
def book_detail(book_id):
    """Book detail page."""
    book = next((b for b in books if b.id == book_id), None)
    if not book:
        flash('Book not found.', 'danger')
        return redirect(url_for('main.index'))
    
    return render_template('book_detail.html', book=book)

@main_bp.route('/book/<int:book_id>/read')
def read_book(book_id):
    """Read book page."""
    book = next((b for b in books if b.id == book_id), None)
    if not book:
        flash('Book not found.', 'danger')
        return redirect(url_for('main.index'))
    
    # Sample content for demonstration
    content = f"""
    <h1>{book.title}</h1>
    <h2>by {book.author}</h2>
    
    <p>This is a sample of the book content for demonstration purposes.</p>
    
    <p>In a real implementation, this would be the actual content of the book loaded from a file.</p>
    
    <p>The book would be properly formatted with chapters, paragraphs, and other elements.</p>
    
    <p>For now, imagine you're reading {book.title} by {book.author}...</p>
    
    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed euismod, nisl vel ultricies lacinia, nisl nisl aliquam nisl, eget aliquam nisl nisl sit amet nisl. Sed euismod, nisl vel ultricies lacinia, nisl nisl aliquam nisl, eget aliquam nisl nisl sit amet nisl.</p>
    
    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed euismod, nisl vel ultricies lacinia, nisl nisl aliquam nisl, eget aliquam nisl nisl sit amet nisl. Sed euismod, nisl vel ultricies lacinia, nisl nisl aliquam nisl, eget aliquam nisl nisl sit amet nisl.</p>
    """
    
    return render_template('read.html', book=book, content=content)

@main_bp.route('/sources')
def sources():
    """Sources page."""
    return render_template('sources.html')

# Authentication routes
@auth_bp.route('/login')
def login():
    """Login page."""
    return render_template('auth/login.html')

@auth_bp.route('/register')
def register():
    """Register page."""
    return render_template('auth/register.html')

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)  # Using port 5001 to avoid conflicts
