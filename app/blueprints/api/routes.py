"""
API routes for Remixable Fiction Library.
This module contains the routes for the API blueprint.
"""

from flask import request, jsonify

from . import api_bp
from app.models.book import Book

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
