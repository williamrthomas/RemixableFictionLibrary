"""
Authentication blueprint for Remixable Fiction Library.
This blueprint handles user authentication routes.
"""

from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

from . import routes
