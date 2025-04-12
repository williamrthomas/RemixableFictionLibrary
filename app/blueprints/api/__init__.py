"""
API blueprint for Remixable Fiction Library.
This blueprint handles API routes for accessing library content.
"""

from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

from . import routes
