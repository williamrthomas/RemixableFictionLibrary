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

class ProjectGutenbergService:
    """Service for interacting with Project Gutenberg catalog and downloads."""
    
    BASE_URL = "https://www.gutenberg.org"
    CATALOG_URL = f"{BASE_URL}/ebooks/search/"
    BOOK_URL = f"{BASE_URL}/ebooks"
    
    # Project Gutenberg has rate limiting, so we need to be careful
    REQUEST_DELAY = 1  # seconds between requests
    
    def __init__(self, cache_dir=None):
        """Initialize the Project Gutenberg service.
        
        Args:
            cache_dir: Directory to cache API responses and downloaded books
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent.parent.parent / "data" / "cache" / "project_gutenberg"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.books_dir = Path(__file__).parent.parent.parent / "data" / "books" / "project_gutenberg"
        self.books_dir.mkdir(parents=True, exist_ok=True)
        self.last_request_time = 0
    
    def _respect_rate_limit(self):
        """Ensure we don't exceed rate limits by adding delays between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def search_books(self, query, use_cache=True):
        """Search for books in the Project Gutenberg catalog.
        
        Args:
            query: Search query string
            use_cache: Whether to use cached data if available
            
        Returns:
            List of matching book metadata dictionaries
        """
        # Create a cache key from the query
        cache_key = re.sub(r'[^a-zA-Z0-9]', '_', query.lower())
        cache_file = self.cache_dir / f"search_{cache_key}.json"
        
        # Check cache first if enabled
        if use_cache and cache_file.exists():
            cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            # Use cache if less than 7 days old
            if cache_age < 604800:  # 7 days in seconds
                logger.info(f"Using cached search results for '{query}'")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        logger.info(f"Searching Project Gutenberg for '{query}'")
        self._respect_rate_limit()
        
        # Perform the search
        params = {
            'query': query,
            'submit_search': 'Go!',
            'include_content': 'fiction'  # Focus on fiction
        }
        
        response = requests.get(self.CATALOG_URL, params=params)
        if response.status_code != 200:
            logger.error(f"Failed to search Project Gutenberg: {response.status_code}")
            return []
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'lxml')
        results = []
        
        # Find all book entries
        for book_element in soup.select('li.booklink'):
            book = {}
            
            # Extract title and author
            title_element = book_element.select_one('span.title')
            if title_element:
                book['title'] = title_element.text.strip()
            
            author_element = book_element.select_one('span.subtitle')
            if author_element:
                book['author'] = author_element.text.strip()
            
            # Extract book ID
            link_element = book_element.select_one('a.link')
            if link_element and 'href' in link_element.attrs:
                href = link_element['href']
                book_id_match = re.search(r'/ebooks/(\d+)', href)
                if book_id_match:
                    book['id'] = book_id_match.group(1)
                    book['url'] = f"{self.BOOK_URL}/{book['id']}"
            
            if 'id' in book:  # Only add if we found an ID
                results.append(book)
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(results, f)
        
        return results
    
    def get_book_details(self, book_id, use_cache=True):
        """Get detailed information about a specific book.
        
        Args:
            book_id: The Project Gutenberg book ID
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary with book details
        """
        cache_file = self.cache_dir / f"book_{book_id}.json"
        
        # Check cache first if enabled
        if use_cache and cache_file.exists():
            cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            # Use cache if less than 7 days old
            if cache_age < 604800:  # 7 days in seconds
                logger.info(f"Using cached book details for {book_id}")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        logger.info(f"Fetching book details for {book_id}")
        self._respect_rate_limit()
        
        # Fetch the book page
        response = requests.get(f"{self.BOOK_URL}/{book_id}")
        if response.status_code != 200:
            logger.error(f"Failed to fetch book details: {response.status_code}")
            return {}
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract book details
        book_details = {
            'id': book_id,
            'url': f"{self.BOOK_URL}/{book_id}",
            'license': 'Project Gutenberg License',
            'downloads': []
        }
        
        # Extract title
        title_element = soup.select_one('h1')
        if title_element:
            book_details['title'] = title_element.text.strip()
        
        # Extract author
        author_element = soup.select_one('h2')
        if author_element:
            book_details['author'] = author_element.text.strip()
        
        # Extract description/bibrec
        bibrec = {}
        bibrec_table = soup.select_one('table.bibrec')
        if bibrec_table:
            for row in bibrec_table.select('tr'):
                cells = row.select('th, td')
                if len(cells) >= 2:
                    key = cells[0].text.strip().lower().replace(' ', '_')
                    value = cells[1].text.strip()
                    bibrec[key] = value
        
        book_details['bibrec'] = bibrec
        
        # Extract publication date if available
        if 'release_date' in bibrec:
            book_details['publication_date'] = bibrec['release_date']
        
        # Extract language if available
        if 'language' in bibrec:
            book_details['language'] = bibrec['language']
        
        # Extract download links
        download_table = soup.select_one('table.files')
        if download_table:
            for row in download_table.select('tr')[1:]:  # Skip header row
                cells = row.select('td')
                if len(cells) >= 2:
                    format_cell = cells[0]
                    link = format_cell.select_one('a')
                    if link and 'href' in link.attrs:
                        book_details['downloads'].append({
                            'format': format_cell.text.strip(),
                            'url': f"{self.BASE_URL}{link['href']}" if not link['href'].startswith('http') else link['href']
                        })
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(book_details, f)
        
        return book_details
    
    def download_book(self, book_id, format='epub'):
        """Download a book from Project Gutenberg.
        
        Args:
            book_id: The Project Gutenberg book ID
            format: The format to download (epub, kindle, html, txt)
            
        Returns:
            Path to the downloaded file, or None if download failed
        """
        # Get book details first to find the download URL
        book_details = self.get_book_details(book_id)
        if not book_details:
            logger.error(f"Failed to get book details for {book_id}")
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
        book_dir = self.books_dir / book_id
        book_dir.mkdir(parents=True, exist_ok=True)
        
        # Download the file
        filename = f"{book_id}.{format}"
        file_path = book_dir / filename
        
        logger.info(f"Downloading {download_url} to {file_path}")
        self._respect_rate_limit()
        
        response = requests.get(download_url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download book: {response.status_code}")
            return None
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded {filename} successfully")
        return file_path
    
    def remove_pg_branding(self, text_content):
        """Remove Project Gutenberg branding from text content.
        
        This is necessary to comply with the Project Gutenberg License for remixing.
        
        Args:
            text_content: The text content of the book
            
        Returns:
            Text content with PG branding removed
        """
        # Common patterns for PG headers and footers
        pg_header_patterns = [
            r"The Project Gutenberg eBook.*?\n\n",
            r"Project Gutenberg's.*?\n\n",
            r"This eBook is for the use of anyone anywhere.*?electronic works\.",
            r"This etext was prepared by.*?\n\n"
        ]
        
        pg_footer_patterns = [
            r"End of the Project Gutenberg EBook.*",
            r"End of Project Gutenberg's.*",
            r"This file should be named.*",
            r"This and all associated files.*",
            r"\*\*\*END OF THE PROJECT GUTENBERG EBOOK.*"
        ]
        
        # Remove headers
        for pattern in pg_header_patterns:
            text_content = re.sub(pattern, "", text_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove footers
        for pattern in pg_footer_patterns:
            text_content = re.sub(pattern, "", text_content, flags=re.DOTALL | re.IGNORECASE)
        
        return text_content.strip()
    
    def get_popular_fiction(self, count=20, use_cache=True):
        """Get a list of popular fiction books from Project Gutenberg.
        
        Args:
            count: Number of books to retrieve
            use_cache: Whether to use cached data if available
            
        Returns:
            List of popular book metadata dictionaries
        """
        cache_file = self.cache_dir / f"popular_fiction_{count}.json"
        
        # Check cache first if enabled
        if use_cache and cache_file.exists():
            cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            # Use cache if less than 1 day old
            if cache_age < 86400:  # 24 hours in seconds
                logger.info(f"Using cached popular fiction list")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        logger.info(f"Fetching popular fiction from Project Gutenberg")
        self._respect_rate_limit()
        
        # Fetch the popular books page
        response = requests.get(f"{self.BASE_URL}/browse/scores/top")
        if response.status_code != 200:
            logger.error(f"Failed to fetch popular books: {response.status_code}")
            return []
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'lxml')
        results = []
        
        # Find all book entries
        for book_element in soup.select('ol.results li'):
            book = {}
            
            # Extract book details
            link_element = book_element.select_one('a')
            if link_element:
                book['title'] = link_element.text.strip()
                if 'href' in link_element.attrs:
                    href = link_element['href']
                    book_id_match = re.search(r'/ebooks/(\d+)', href)
                    if book_id_match:
                        book['id'] = book_id_match.group(1)
                        book['url'] = f"{self.BOOK_URL}/{book['id']}"
            
            # Extract author
            author_element = book_element.select_one('span.subtitle')
            if author_element:
                book['author'] = author_element.text.strip()
            
            if 'id' in book:  # Only add if we found an ID
                results.append(book)
                
                if len(results) >= count:
                    break
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(results, f)
        
        return results
