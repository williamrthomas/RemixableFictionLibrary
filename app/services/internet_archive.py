import os
import requests
import json
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InternetArchiveService:
    """Service for interacting with Internet Archive API and website.
    
    This service requires careful verification of content licensing.
    """
    
    BASE_URL = "https://archive.org"
    SEARCH_URL = f"{BASE_URL}/advancedsearch.php"
    METADATA_URL = f"{BASE_URL}/metadata"
    
    # Internet Archive has rate limiting, so we need to be careful
    REQUEST_DELAY = 1  # seconds between requests
    
    def __init__(self, cache_dir=None):
        """Initialize the Internet Archive service.
        
        Args:
            cache_dir: Directory to cache API responses and downloaded books
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent.parent.parent / "data" / "cache" / "internet_archive"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.books_dir = Path(__file__).parent.parent.parent / "data" / "books" / "internet_archive"
        self.books_dir.mkdir(parents=True, exist_ok=True)
        self.last_request_time = 0
    
    def _respect_rate_limit(self):
        """Ensure we don't exceed rate limits by adding delays between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def search_books(self, query, use_cache=True, verify_pd=True):
        """Search for books in the Internet Archive.
        
        Args:
            query: Search query string
            use_cache: Whether to use cached data if available
            verify_pd: Whether to filter for likely public domain works (pre-1929)
            
        Returns:
            List of matching book metadata dictionaries
        """
        # Create a cache key from the query
        cache_key = re.sub(r'[^a-zA-Z0-9]', '_', query.lower())
        cache_file = self.cache_dir / f"search_{cache_key}_pd{verify_pd}.json"
        
        # Check cache first if enabled
        if use_cache and cache_file.exists():
            cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            # Use cache if less than 3 days old
            if cache_age < 259200:  # 3 days in seconds
                logger.info(f"Using cached search results for '{query}'")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        logger.info(f"Searching Internet Archive for '{query}'")
        self._respect_rate_limit()
        
        # Build the query
        search_query = f"{query} AND mediatype:texts"
        
        # If verifying for public domain, add date filter
        if verify_pd:
            search_query += " AND date:[1800 TO 1928]"
        
        # Perform the search
        params = {
            'q': search_query,
            'fl[]': ['identifier', 'title', 'creator', 'date', 'description', 'subject', 'collection'],
            'sort[]': ['downloads desc'],
            'rows': 50,
            'page': 1,
            'output': 'json'
        }
        
        response = requests.get(self.SEARCH_URL, params=params)
        if response.status_code != 200:
            logger.error(f"Failed to search Internet Archive: {response.status_code}")
            return []
        
        try:
            data = response.json()
            results = []
            
            for doc in data.get('response', {}).get('docs', []):
                book = {
                    'id': doc.get('identifier', ''),
                    'title': doc.get('title', ''),
                    'author': doc.get('creator', ''),
                    'date': doc.get('date', ''),
                    'description': doc.get('description', ''),
                    'subject': doc.get('subject', []),
                    'collection': doc.get('collection', []),
                    'url': f"{self.BASE_URL}/details/{doc.get('identifier', '')}"
                }
                results.append(book)
            
            # Cache the results
            with open(cache_file, 'w') as f:
                json.dump(results, f)
            
            return results
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
            return []
    
    def get_book_details(self, identifier, use_cache=True):
        """Get detailed information about a specific book.
        
        Args:
            identifier: The Internet Archive identifier
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary with book details including verification information
        """
        cache_file = self.cache_dir / f"book_{identifier}.json"
        
        # Check cache first if enabled
        if use_cache and cache_file.exists():
            cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            # Use cache if less than 7 days old
            if cache_age < 604800:  # 7 days in seconds
                logger.info(f"Using cached book details for {identifier}")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        logger.info(f"Fetching book details for {identifier}")
        self._respect_rate_limit()
        
        # Fetch the metadata
        response = requests.get(f"{self.METADATA_URL}/{identifier}")
        if response.status_code != 200:
            logger.error(f"Failed to fetch book metadata: {response.status_code}")
            return {}
        
        try:
            data = response.json()
            metadata = data.get('metadata', {})
            
            # Extract book details
            book_details = {
                'id': identifier,
                'url': f"{self.BASE_URL}/details/{identifier}",
                'title': metadata.get('title', ''),
                'author': metadata.get('creator', ''),
                'date': metadata.get('date', ''),
                'description': metadata.get('description', ''),
                'subject': metadata.get('subject', []),
                'collection': metadata.get('collection', []),
                'downloads': []
            }
            
            # Extract files information
            files = data.get('files', [])
            for file in files:
                if file.get('format') in ['Text PDF', 'EPUB', 'MOBI', 'Kindle', 'DjVu', 'HTML', 'Plain Text']:
                    book_details['downloads'].append({
                        'format': file.get('format', ''),
                        'name': file.get('name', ''),
                        'url': f"{self.BASE_URL}/download/{identifier}/{file.get('name', '')}"
                    })
            
            # Perform license verification
            book_details['license_verification'] = self._verify_license(metadata)
            
            # Cache the results
            with open(cache_file, 'w') as f:
                json.dump(book_details, f)
            
            return book_details
        except Exception as e:
            logger.error(f"Error parsing book details: {e}")
            return {}
    
    def _verify_license(self, metadata):
        """Verify the license status of a book.
        
        Args:
            metadata: Book metadata from Internet Archive
            
        Returns:
            Dictionary with license verification information
        """
        verification = {
            'is_verified': False,
            'license_type': 'unknown',
            'confidence': 'low',
            'notes': []
        }
        
        # Check for explicit license information
        if 'licenseurl' in metadata:
            license_url = metadata['licenseurl']
            if 'creativecommons.org/publicdomain/zero' in license_url:
                verification['license_type'] = 'CC0'
                verification['notes'].append('CC0 license URL found in metadata')
                verification['confidence'] = 'medium'
            elif 'creativecommons.org/licenses/by/' in license_url and 'nd' not in license_url:
                verification['license_type'] = 'CC BY'
                verification['notes'].append('CC BY license URL found in metadata')
                verification['confidence'] = 'medium'
            elif 'creativecommons.org/licenses/by-sa/' in license_url:
                verification['license_type'] = 'CC BY-SA'
                verification['notes'].append('CC BY-SA license URL found in metadata')
                verification['confidence'] = 'medium'
        
        # Check publication date for public domain status
        if 'date' in metadata:
            date_str = metadata['date']
            year_match = re.search(r'\b(1[0-9]{3}|20[0-2][0-9])\b', date_str)
            if year_match:
                year = int(year_match.group(1))
                if year < 1929:
                    verification['notes'].append(f'Publication year {year} suggests US public domain status')
                    if verification['license_type'] == 'unknown':
                        verification['license_type'] = 'US PD'
                    verification['confidence'] = 'medium' if verification['confidence'] == 'low' else verification['confidence']
        
        # Check for public domain text in description
        if 'description' in metadata:
            desc = metadata['description'].lower()
            if 'public domain' in desc or 'not copyrighted' in desc:
                verification['notes'].append('Public domain mentioned in description')
                if verification['license_type'] == 'unknown':
                    verification['license_type'] = 'US PD'
                verification['confidence'] = 'medium' if verification['confidence'] == 'low' else verification['confidence']
        
        # Check for Project Gutenberg as source
        collections = metadata.get('collection', [])
        if isinstance(collections, str):
            collections = [collections]
        
        for collection in collections:
            if 'gutenberg' in collection.lower():
                verification['notes'].append('Part of Project Gutenberg collection')
                if verification['license_type'] == 'unknown':
                    verification['license_type'] = 'US PD'
                verification['confidence'] = 'high'
        
        # Set verification status based on confidence and license type
        if verification['confidence'] in ['medium', 'high'] and verification['license_type'] != 'unknown':
            verification['is_verified'] = True
        
        return verification
    
    def download_book(self, identifier, format='epub'):
        """Download a book from Internet Archive.
        
        Args:
            identifier: The Internet Archive identifier
            format: The format to download (epub, pdf, txt, etc.)
            
        Returns:
            Path to the downloaded file, or None if download failed
        """
        # Get book details first to find the download URL
        book_details = self.get_book_details(identifier)
        if not book_details:
            logger.error(f"Failed to get book details for {identifier}")
            return None
        
        # Verify license status
        verification = book_details.get('license_verification', {})
        if not verification.get('is_verified', False):
            logger.warning(f"Book {identifier} has unverified license status. Use with caution.")
        
        # Find the download URL for the requested format
        download_url = None
        file_name = None
        for download in book_details.get('downloads', []):
            if format.lower() in download.get('format', '').lower():
                download_url = download.get('url')
                file_name = download.get('name')
                break
        
        if not download_url:
            logger.error(f"No download URL found for format {format}")
            return None
        
        # Create a directory for this book
        book_dir = self.books_dir / identifier
        book_dir.mkdir(parents=True, exist_ok=True)
        
        # Download the file
        file_path = book_dir / file_name
        
        logger.info(f"Downloading {download_url} to {file_path}")
        self._respect_rate_limit()
        
        response = requests.get(download_url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download book: {response.status_code}")
            return None
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded {file_name} successfully")
        return file_path
    
    def get_pd_fiction_collections(self, use_cache=True):
        """Get a list of collections likely to contain public domain fiction.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            List of collection identifiers and names
        """
        cache_file = self.cache_dir / "pd_fiction_collections.json"
        
        # Check cache first if enabled
        if use_cache and cache_file.exists():
            cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            # Use cache if less than 30 days old
            if cache_age < 2592000:  # 30 days in seconds
                logger.info("Using cached PD fiction collections")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        logger.info("Fetching public domain fiction collections")
        
        # Known collections likely to contain PD fiction
        collections = [
            {
                'id': 'gutenberg',
                'name': 'Project Gutenberg',
                'description': 'Books from Project Gutenberg',
                'confidence': 'high'
            },
            {
                'id': 'americana',
                'name': 'American Libraries',
                'description': 'American libraries collection',
                'confidence': 'medium'
            },
            {
                'id': 'toronto',
                'name': 'Canadian Libraries',
                'description': 'Canadian libraries collection',
                'confidence': 'medium'
            },
            {
                'id': 'librivoxaudio',
                'name': 'LibriVox Audio',
                'description': 'LibriVox public domain audiobooks',
                'confidence': 'high'
            }
        ]
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(collections, f)
        
        return collections
