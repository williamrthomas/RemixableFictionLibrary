"""
Main blueprint for Remixable Fiction Library.
This blueprint handles the main public-facing routes.
"""

from flask import Blueprint

main_bp = Blueprint('main', __name__)

from . import routes
