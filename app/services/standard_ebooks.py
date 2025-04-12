import os
import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StandardEbooksService:
    """Service for interacting with Standard Ebooks API and website."""
    
    BASE_URL = "https://standardebooks.org"
    EBOOKS_URL = f"{BASE_URL}/ebooks"
    API_URL = f"{BASE_URL}/opds"
    
    def __init__(self, cache_dir=None):
        """Initialize the Standard Ebooks service.
        
        Args:
            cache_dir: Directory to cache API responses and downloaded books
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent.parent.parent / "data" / "cache" / "standard_ebooks"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.books_dir = Path(__file__).parent.parent.parent / "data" / "books" / "standard_ebooks"
        self.books_dir.mkdir(parents=True, exist_ok=True)
    
    def get_all_books(self, use_cache=True):
        """Get all books from Standard Ebooks.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            List of book metadata dictionaries
        """
        cache_file = self.cache_dir / "all_books.json"
        
        # Check cache first if enabled
        if use_cache and cache_file.exists():
            cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            # Use cache if less than 1 day old
            if cache_age < 86400:  # 24 hours in seconds
                logger.info("Using cached Standard Ebooks catalog")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        logger.info("Fetching Standard Ebooks catalog")
        
        # Fetch the OPDS feed
        response = requests.get(self.API_URL)
        if response.status_code != 200:
            logger.error(f"Failed to fetch Standard Ebooks catalog: {response.status_code}")
            return []
        
        # Parse the XML feed
        soup = BeautifulSoup(response.content, 'lxml-xml')
        entries = soup.find_all('entry')
        
        books = []
        for entry in entries:
            # Skip non-book entries
            if not entry.find('link', {'type': 'application/epub+zip'}):
                continue
                
            book = {
                'title': entry.find('title').text if entry.find('title') else '',
                'author': entry.find('author').find('name').text if entry.find('author') else '',
                'id': entry.find('id').text if entry.find('id') else '',
                'updated': entry.find('updated').text if entry.find('updated') else '',
                'summary': entry.find('summary').text if entry.find('summary') else '',
                'content': entry.find('content').text if entry.find('content') else '',
                'links': [
                    {
                        'href': link['href'],
                        'type': link['type'],
                        'rel': link.get('rel', '')
                    }
                    for link in entry.find_all('link')
                ]
            }
            
            # Extract the URL identifier
            for link in book['links']:
                if link['type'] == 'text/html' and link['rel'] == 'alternate':
                    book['url_identifier'] = link['href'].replace(self.BASE_URL, '')
                    break
            
            books.append(book)
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(books, f)
        
        return books
    
    def get_book_details(self, url_identifier, use_cache=True):
        """Get detailed information about a specific book.
        
        Args:
            url_identifier: The URL identifier for the book (e.g., "/ebooks/jane-austen/pride-and-prejudice")
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary with book details
        """
        # Clean up the identifier if needed
        if url_identifier.startswith(self.BASE_URL):
            url_identifier = url_identifier.replace(self.BASE_URL, '')
        
        cache_file = self.cache_dir / f"book_{url_identifier.replace('/', '_')}.json"
        
        # Check cache first if enabled
        if use_cache and cache_file.exists():
            cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            # Use cache if less than 7 days old
            if cache_age < 604800:  # 7 days in seconds
                logger.info(f"Using cached book details for {url_identifier}")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        logger.info(f"Fetching book details for {url_identifier}")
        
        # Fetch the book page
        response = requests.get(f"{self.BASE_URL}{url_identifier}")
        if response.status_code != 200:
            logger.error(f"Failed to fetch book details: {response.status_code}")
            return {}
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract book details
        book_details = {
            'title': soup.find('h1', class_='title').text.strip() if soup.find('h1', class_='title') else '',
            'author': soup.find('h2', class_='author').text.strip() if soup.find('h2', class_='author') else '',
            'url': f"{self.BASE_URL}{url_identifier}",
            'description': soup.find('section', id='description').text.strip() if soup.find('section', id='description') else '',
            'license': 'CC0',  # Standard Ebooks uses CC0 for all their enhancements
            'downloads': []
        }
        
        # Extract download links
        download_section = soup.find('section', id='download')
        if download_section:
            for link in download_section.find_all('a'):
                if 'href' in link.attrs:
                    book_details['downloads'].append({
                        'format': link.text.strip(),
                        'url': f"{self.BASE_URL}{link['href']}" if not link['href'].startswith('http') else link['href']
                    })
        
        # Extract metadata
        metadata_section = soup.find('section', id='metadata')
        if metadata_section:
            book_details['metadata'] = {}
            for dl in metadata_section.find_all('dl'):
                for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
                    key = dt.text.strip().lower().replace(' ', '_')
                    book_details['metadata'][key] = dd.text.strip()
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(book_details, f)
        
        return book_details
    
    def download_book(self, url_identifier, format='epub'):
        """Download a book from Standard Ebooks.
        
        Args:
            url_identifier: The URL identifier for the book
            format: The format to download (epub, azw3, kepub, etc.)
            
        Returns:
            Path to the downloaded file, or None if download failed
        """
        # Get book details first to find the download URL
        book_details = self.get_book_details(url_identifier)
        if not book_details:
            logger.error(f"Failed to get book details for {url_identifier}")
            return None
        
        # Find the download URL for the requested format
        download_url = None
        for download in book_details.get('downloads', []):
            if format.lower() in download.get('format', '').lower():
                download_url = download.get('url')
                break
        
        if not download_url:
            logger.error(f"No download URL found for format {format}")
            return None
        
        # Create a directory for this book
        book_dir = self.books_dir / url_identifier.strip('/').split('/')[-1]
        book_dir.mkdir(parents=True, exist_ok=True)
        
        # Download the file
        filename = download_url.split('/')[-1]
        file_path = book_dir / filename
        
        logger.info(f"Downloading {download_url} to {file_path}")
        response = requests.get(download_url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download book: {response.status_code}")
            return None
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded {filename} successfully")
        return file_path
    
    def search_books(self, query):
        """Search for books in the Standard Ebooks catalog.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching book metadata dictionaries
        """
        # Get all books first
        all_books = self.get_all_books()
        
        # Simple search implementation - could be improved with better text matching
        query = query.lower()
        results = []
        
        for book in all_books:
            # Search in title and author
            if (query in book.get('title', '').lower() or 
                query in book.get('author', '').lower() or
                query in book.get('summary', '').lower()):
                results.append(book)
        
        return results
