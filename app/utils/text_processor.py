import re
import logging
import html
import markdown
from bs4 import BeautifulSoup
from pathlib import Path
import ebooklib
from ebooklib import epub

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextProcessor:
    """Utility for processing and converting text content from various sources."""
    
    def __init__(self):
        """Initialize the text processor."""
        pass
    
    def clean_text(self, text):
        """Clean text content by removing extra whitespace, normalizing line breaks, etc.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Replace multiple spaces with a single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with at most two
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def html_to_text(self, html_content):
        """Convert HTML content to plain text.
        
        Args:
            html_content: HTML content
            
        Returns:
            Plain text
        """
        if not html_content:
            return ""
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up text
        text = self.clean_text(text)
        
        return text
    
    def text_to_html(self, text, title=None, author=None):
        """Convert plain text to HTML.
        
        Args:
            text: Plain text content
            title: Optional title for the HTML document
            author: Optional author for the HTML document
            
        Returns:
            HTML content
        """
        if not text:
            return ""
        
        # Escape HTML entities
        text = html.escape(text)
        
        # Convert paragraphs (blank lines) to <p> tags
        paragraphs = text.split('\n\n')
        html_paragraphs = [f"<p>{p.replace('\n', '<br>')}</p>" for p in paragraphs if p.strip()]
        
        # Build HTML document
        html_content = []
        html_content.append("<!DOCTYPE html>")
        html_content.append("<html>")
        html_content.append("<head>")
        
        if title:
            html_content.append(f"<title>{html.escape(title)}</title>")
        
        html_content.append("<meta charset=\"utf-8\">")
        html_content.append("<style>")
        html_content.append("body { font-family: Georgia, serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 1em; }")
        html_content.append("h1 { text-align: center; }")
        html_content.append("h2 { text-align: center; }")
        html_content.append("</style>")
        html_content.append("</head>")
        html_content.append("<body>")
        
        if title:
            html_content.append(f"<h1>{html.escape(title)}</h1>")
        
        if author:
            html_content.append(f"<h2>by {html.escape(author)}</h2>")
        
        html_content.extend(html_paragraphs)
        
        html_content.append("</body>")
        html_content.append("</html>")
        
        return "\n".join(html_content)
    
    def markdown_to_html(self, markdown_content, title=None, author=None):
        """Convert Markdown content to HTML.
        
        Args:
            markdown_content: Markdown content
            title: Optional title for the HTML document
            author: Optional author for the HTML document
            
        Returns:
            HTML content
        """
        if not markdown_content:
            return ""
        
        # Convert Markdown to HTML
        html_body = markdown.markdown(markdown_content)
        
        # Build HTML document
        html_content = []
        html_content.append("<!DOCTYPE html>")
        html_content.append("<html>")
        html_content.append("<head>")
        
        if title:
            html_content.append(f"<title>{html.escape(title)}</title>")
        
        html_content.append("<meta charset=\"utf-8\">")
        html_content.append("<style>")
        html_content.append("body { font-family: Georgia, serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 1em; }")
        html_content.append("h1 { text-align: center; }")
        html_content.append("h2 { text-align: center; }")
        html_content.append("</style>")
        html_content.append("</head>")
        html_content.append("<body>")
        
        if title:
            html_content.append(f"<h1>{html.escape(title)}</h1>")
        
        if author:
            html_content.append(f"<h2>by {html.escape(author)}</h2>")
        
        html_content.append(html_body)
        
        html_content.append("</body>")
        html_content.append("</html>")
        
        return "\n".join(html_content)
    
    def create_epub(self, title, author, content, output_path, cover_image=None, language='en'):
        """Create an EPUB file from content.
        
        Args:
            title: Book title
            author: Book author
            content: Book content (HTML)
            output_path: Path to save the EPUB file
            cover_image: Optional path to cover image
            language: Book language code
            
        Returns:
            Path to the created EPUB file
        """
        # Create a new EPUB book
        book = epub.EpubBook()
        
        # Set metadata
        book.set_title(title)
        book.set_language(language)
        book.add_author(author)
        
        # Add cover if provided
        if cover_image and Path(cover_image).exists():
            with open(cover_image, 'rb') as f:
                book.set_cover('cover.jpg', f.read())
        
        # Create a chapter
        c1 = epub.EpubHtml(title=title, file_name='content.xhtml')
        c1.content = content
        
        # Add chapter to the book
        book.add_item(c1)
        
        # Define Table of Contents
        book.toc = [epub.Link('content.xhtml', title, 'content')]
        
        # Add default NCX and Nav files
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # Define CSS style
        style = '''
            body {
                font-family: Georgia, serif;
                line-height: 1.6;
                margin: 1em;
            }
            h1 {
                text-align: center;
                font-size: 1.5em;
            }
            h2 {
                text-align: center;
                font-size: 1.2em;
            }
        '''
        
        # Add CSS file
        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style
        )
        book.add_item(nav_css)
        
        # Create spine
        book.spine = ['nav', c1]
        
        # Create the EPUB file
        epub.write_epub(output_path, book, {})
        
        return output_path
    
    def extract_epub_content(self, epub_path):
        """Extract content from an EPUB file.
        
        Args:
            epub_path: Path to the EPUB file
            
        Returns:
            Dictionary with book metadata and content
        """
        try:
            # Load the EPUB file
            book = epub.read_epub(epub_path)
            
            # Extract metadata
            metadata = {
                'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else '',
                'author': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else '',
                'language': book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else '',
                'identifier': book.get_metadata('DC', 'identifier')[0][0] if book.get_metadata('DC', 'identifier') else '',
                'publisher': book.get_metadata('DC', 'publisher')[0][0] if book.get_metadata('DC', 'publisher') else '',
                'date': book.get_metadata('DC', 'date')[0][0] if book.get_metadata('DC', 'date') else '',
                'description': book.get_metadata('DC', 'description')[0][0] if book.get_metadata('DC', 'description') else '',
                'rights': book.get_metadata('DC', 'rights')[0][0] if book.get_metadata('DC', 'rights') else '',
            }
            
            # Extract content
            content = []
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content.append({
                        'id': item.get_id(),
                        'name': item.get_name(),
                        'content': item.get_content().decode('utf-8')
                    })
            
            return {
                'metadata': metadata,
                'content': content
            }
        except Exception as e:
            logger.error(f"Error extracting EPUB content: {e}")
            return {
                'metadata': {},
                'content': []
            }
    
    def extract_text_from_epub(self, epub_path):
        """Extract plain text from an EPUB file.
        
        Args:
            epub_path: Path to the EPUB file
            
        Returns:
            Plain text content
        """
        book_data = self.extract_epub_content(epub_path)
        
        text_content = []
        for item in book_data.get('content', []):
            html_content = item.get('content', '')
            text_content.append(self.html_to_text(html_content))
        
        return "\n\n".join(text_content)
    
    def split_into_chapters(self, text, chapter_markers=None):
        """Split text into chapters based on markers.
        
        Args:
            text: Text content
            chapter_markers: List of regex patterns for chapter headings
            
        Returns:
            List of chapters
        """
        if not text:
            return []
        
        if not chapter_markers:
            # Default chapter markers
            chapter_markers = [
                r'^CHAPTER [IVXLCDM]+\.?',  # CHAPTER I, CHAPTER II, etc.
                r'^CHAPTER \d+\.?',         # CHAPTER 1, CHAPTER 2, etc.
                r'^Chapter [IVXLCDM]+\.?',  # Chapter I, Chapter II, etc.
                r'^Chapter \d+\.?',         # Chapter 1, Chapter 2, etc.
                r'^\d+\.',                  # 1., 2., etc.
                r'^[IVXLCDM]+\.',           # I., II., etc.
            ]
        
        # Combine all patterns
        combined_pattern = '|'.join(f'({pattern})' for pattern in chapter_markers)
        
        # Find all chapter starts
        chapter_starts = []
        for match in re.finditer(combined_pattern, text, re.MULTILINE):
            chapter_starts.append(match.start())
        
        # If no chapters found, return the whole text as one chapter
        if not chapter_starts:
            return [text]
        
        # Split text into chapters
        chapters = []
        for i in range(len(chapter_starts)):
            start = chapter_starts[i]
            end = chapter_starts[i+1] if i+1 < len(chapter_starts) else len(text)
            chapters.append(text[start:end].strip())
        
        return chapters
