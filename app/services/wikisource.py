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

class WikisourceService:
    """Service for interacting with Wikisource API and website.
    
    This service handles works with CC BY-SA licensing.
    """
    
    BASE_URL = "https://en.wikisource.org"
    API_URL = f"{BASE_URL}/w/api.php"
    
    # Wikisource has rate limiting, so we need to be careful
    REQUEST_DELAY = 1  # seconds between requests
    
    def __init__(self, cache_dir=None):
        """Initialize the Wikisource service.
        
        Args:
            cache_dir: Directory to cache API responses and downloaded content
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent.parent.parent / "data" / "cache" / "wikisource"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.books_dir = Path(__file__).parent.parent.parent / "data" / "books" / "wikisource"
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
        """Search for books in Wikisource.
        
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
            # Use cache if less than 3 days old
            if cache_age < 259200:  # 3 days in seconds
                logger.info(f"Using cached search results for '{query}'")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        logger.info(f"Searching Wikisource for '{query}'")
        self._respect_rate_limit()
        
        # Perform the search using the Wikisource API
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': query,
            'srnamespace': '0|100',  # Main namespace and Portal namespace
            'srlimit': 50,
            'format': 'json'
        }
        
        response = requests.get(self.API_URL, params=params)
        if response.status_code != 200:
            logger.error(f"Failed to search Wikisource: {response.status_code}")
            return []
        
        try:
            data = response.json()
            results = []
            
            for item in data.get('query', {}).get('search', []):
                title = item.get('title', '')
                
                # Skip non-book pages
                if ':' in title and not title.startswith('Portal:'):
                    continue
                    
                book = {
                    'title': title,
                    'snippet': BeautifulSoup(item.get('snippet', ''), 'lxml').text,
                    'url': f"{self.BASE_URL}/wiki/{title.replace(' ', '_')}",
                    'page_id': item.get('pageid', '')
                }
                results.append(book)
            
            # Cache the results
            with open(cache_file, 'w') as f:
                json.dump(results, f)
            
            return results
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
            return []
    
    def get_book_details(self, title, use_cache=True):
        """Get detailed information about a specific book.
        
        Args:
            title: The Wikisource page title
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary with book details
        """
        # Normalize the title
        title = title.replace(' ', '_')
        
        cache_file = self.cache_dir / f"book_{title}.json"
        
        # Check cache first if enabled
        if use_cache and cache_file.exists():
            cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            # Use cache if less than 7 days old
            if cache_age < 604800:  # 7 days in seconds
                logger.info(f"Using cached book details for {title}")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        logger.info(f"Fetching book details for {title}")
        self._respect_rate_limit()
        
        # Fetch the book page
        response = requests.get(f"{self.BASE_URL}/wiki/{title}")
        if response.status_code != 200:
            logger.error(f"Failed to fetch book details: {response.status_code}")
            return {}
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract book details
        book_details = {
            'title': title.replace('_', ' '),
            'url': f"{self.BASE_URL}/wiki/{title}",
            'license': 'CC BY-SA',  # Wikisource content is generally CC BY-SA
            'content': '',
            'sections': []
        }
        
        # Extract the main content
        content_div = soup.select_one('#mw-content-text')
        if content_div:
            # Check if this is an index page
            index_pages = content_div.select('.prp-pages-output a')
            if index_pages:
                for link in index_pages:
                    if 'href' in link.attrs:
                        section_title = link.text.strip()
                        section_url = link['href']
                        if section_url.startswith('/'):
                            section_url = f"{self.BASE_URL}{section_url}"
                        book_details['sections'].append({
                            'title': section_title,
                            'url': section_url
                        })
            else:
                # This is a content page
                # Remove edit links, reference numbers, etc.
                for element in content_div.select('.mw-editsection, .reference'):
                    element.decompose()
                
                book_details['content'] = content_div.text.strip()
        
        # Extract author information
        author_element = soup.select_one('#headerContainer .headertemplate-author')
        if author_element:
            book_details['author'] = author_element.text.strip()
        
        # Extract publication date if available
        date_element = soup.select_one('#headerContainer .headertemplate-date')
        if date_element:
            book_details['publication_date'] = date_element.text.strip()
        
        # Check for license information
        license_element = soup.select_one('.licensetpl_short')
        if license_element:
            license_text = license_element.text.strip()
            if 'CC BY-SA' in license_text:
                book_details['license'] = 'CC BY-SA'
            elif 'CC0' in license_text:
                book_details['license'] = 'CC0'
            elif 'public domain' in license_text.lower():
                book_details['license'] = 'US PD'
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(book_details, f)
        
        return book_details
    
    def download_book(self, title, format='html'):
        """Download a book from Wikisource.
        
        Args:
            title: The Wikisource page title
            format: The format to download (html, txt)
            
        Returns:
            Path to the downloaded file, or None if download failed
        """
        # Normalize the title
        title = title.replace(' ', '_')
        
        # Get book details first
        book_details = self.get_book_details(title)
        if not book_details:
            logger.error(f"Failed to get book details for {title}")
            return None
        
        # Create a directory for this book
        book_dir = self.books_dir / title
        book_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine if this is an index page or a content page
        if book_details.get('sections', []):
            # This is an index page, we need to download all sections
            logger.info(f"Downloading multi-section book: {title}")
            
            # Create an index file
            index_path = book_dir / f"{title}_index.html"
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(f"<html><head><title>{book_details['title']}</title></head><body>\n")
                f.write(f"<h1>{book_details['title']}</h1>\n")
                
                if 'author' in book_details:
                    f.write(f"<p>Author: {book_details['author']}</p>\n")
                
                f.write("<h2>Contents</h2>\n<ul>\n")
                
                # Download each section
                all_content = ""
                for i, section in enumerate(book_details['sections']):
                    section_title = section['title']
                    section_url = section['url']
                    
                    # Extract the page title from the URL
                    section_page = section_url.split('/')[-1]
                    
                    f.write(f'<li><a href="{section_page}.html">{section_title}</a></li>\n')
                    
                    # Download the section content
                    self._respect_rate_limit()
                    response = requests.get(section_url)
                    if response.status_code == 200:
                        section_soup = BeautifulSoup(response.content, 'lxml')
                        content_div = section_soup.select_one('#mw-content-text')
                        
                        if content_div:
                            # Remove edit links, reference numbers, etc.
                            for element in content_div.select('.mw-editsection, .reference'):
                                element.decompose()
                            
                            section_content = content_div.text.strip()
                            
                            # Save the section content
                            section_path = book_dir / f"{section_page}.html"
                            with open(section_path, 'w', encoding='utf-8') as section_file:
                                section_file.write(f"<html><head><title>{section_title}</title></head><body>\n")
                                section_file.write(f"<h1>{section_title}</h1>\n")
                                section_file.write(f"<div>{content_div.decode_contents()}</div>\n")
                                section_file.write(f'<p><a href="{title}_index.html">Back to index</a></p>\n')
                                section_file.write("</body></html>")
                            
                            all_content += f"\n\n{section_title}\n\n{section_content}"
                    else:
                        logger.error(f"Failed to download section {section_title}: {response.status_code}")
                
                f.write("</ul>\n")
                f.write("<p>License: CC BY-SA 3.0</p>\n")
                f.write("<p>Source: Wikisource</p>\n")
                f.write("</body></html>")
            
            # Also save a text version if requested
            if format.lower() == 'txt':
                txt_path = book_dir / f"{title}.txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(f"{book_details['title']}\n\n")
                    if 'author' in book_details:
                        f.write(f"Author: {book_details['author']}\n\n")
                    f.write(all_content)
                
                return txt_path
            
            return index_path
        else:
            # This is a content page
            if format.lower() == 'html':
                file_path = book_dir / f"{title}.html"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"<html><head><title>{book_details['title']}</title></head><body>\n")
                    f.write(f"<h1>{book_details['title']}</h1>\n")
                    
                    if 'author' in book_details:
                        f.write(f"<p>Author: {book_details['author']}</p>\n")
                    
                    f.write(f"<div>{book_details['content']}</div>\n")
                    f.write("<p>License: CC BY-SA 3.0</p>\n")
                    f.write("<p>Source: Wikisource</p>\n")
                    f.write("</body></html>")
            else:
                file_path = book_dir / f"{title}.txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"{book_details['title']}\n\n")
                    
                    if 'author' in book_details:
                        f.write(f"Author: {book_details['author']}\n\n")
                    
                    f.write(book_details['content'])
            
            logger.info(f"Downloaded {title} successfully")
            return file_path
    
    def get_featured_works(self, use_cache=True):
        """Get a list of featured works from Wikisource.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            List of featured work metadata dictionaries
        """
        cache_file = self.cache_dir / "featured_works.json"
        
        # Check cache first if enabled
        if use_cache and cache_file.exists():
            cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            # Use cache if less than 7 days old
            if cache_age < 604800:  # 7 days in seconds
                logger.info("Using cached featured works")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        logger.info("Fetching featured works from Wikisource")
        self._respect_rate_limit()
        
        # Fetch the featured works page
        response = requests.get(f"{self.BASE_URL}/wiki/Wikisource:Featured_texts")
        if response.status_code != 200:
            logger.error(f"Failed to fetch featured works: {response.status_code}")
            return []
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'lxml')
        results = []
        
        # Find featured works
        featured_div = soup.select_one('#mw-content-text')
        if featured_div:
            for link in featured_div.select('a'):
                if 'href' in link.attrs and link['href'].startswith('/wiki/') and ':' not in link['href']:
                    title = link.text.strip()
                    url = link['href']
                    
                    # Skip empty titles and special pages
                    if not title or title in ['edit', 'view', 'history']:
                        continue
                    
                    results.append({
                        'title': title,
                        'url': f"{self.BASE_URL}{url}"
                    })
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(results, f)
        
        return results
