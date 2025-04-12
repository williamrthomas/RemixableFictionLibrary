# Remixable Fiction Library

A digital library of free, accessible, and remixable fiction works, inspired by the Wikipedia collaborative model.

![Remixable Fiction Library](https://via.placeholder.com/800x400?text=Remixable+Fiction+Library)

## About

This project aims to build a dynamic, "Wikipedia-style" reference library dedicated to freely available, easily accessible, and openly licensed novels and stories. It focuses specifically on literary works whose copyright status permits remixing and the creation of derivative works.

## Version 0.5 Release

This is the initial public release (v0.5) of the Remixable Fiction Library. Key features in this version:

- Open access system with no login required for browsing and reading content
- Blueprint architecture for improved code organization and maintenance
- Proper database configuration with SQLite
- Basic content browsing and reading functionality
- License verification workflow
- Admin-only import functionality

## Features

- Collection of works from the US Public Domain and with permissive Creative Commons licenses (CC0, CC BY, CC BY-SA)
- Integration with major sources of free literature:
  - Standard Ebooks (primary source - highest quality, CC0 license)
  - Project Gutenberg (secondary source - vast collection, US PD)
  - Internet Archive (with careful verification)
  - Wikisource (with CC BY-SA considerations)
- License verification workflow
- Proper attribution system
- Web interface for browsing, searching, and viewing books
- API for accessing and remixing content
- User authentication and personalization
- Responsive design for mobile and desktop

## License Sources

The library prioritizes works from the following sources:

1. **Standard Ebooks**: High-quality, accessible ebook editions with CC0 licensing
2. **Project Gutenberg**: Classic literature in the US public domain
3. **Internet Archive**: Selected works with verified public domain or open license status
4. **Wikisource**: Collaborative transcriptions with CC BY-SA licensing

## Technical Stack

- **Backend**: Python 3.13 with Flask
- **Database**: SQLAlchemy with SQLite (PostgreSQL for production)
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Authentication**: Flask-Login
- **Text Processing**: BeautifulSoup, EbookLib, Markdown
- **Deployment**: Gunicorn (for production)

## Project Structure

```
RemixableFictionLibrary/
├── app/                    # Main application package
│   ├── __init__.py         # Application factory
│   ├── auth/               # Authentication blueprint
│   ├── main/               # Main routes blueprint
│   ├── admin/              # Admin interface blueprint
│   ├── models/             # Database models
│   ├── services/           # External API services
│   ├── utils/              # Utility functions
│   ├── static/             # Static files (CSS, JS, images)
│   └── templates/          # Jinja2 templates
├── data/                   # SQLite database and data files
├── migrations/             # Database migrations
├── tests/                  # Test suite
├── .env                    # Environment variables
├── run.py                  # Application entry point
├── demo.py                 # Demo application (no database)
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Getting Started

### Prerequisites

- Python 3.13 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/RemixableFictionLibrary.git
   cd RemixableFictionLibrary
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with the following content:
   ```
   SECRET_KEY=your-secret-key
   FLASK_APP=app
   FLASK_ENV=development
   DATABASE_URI=sqlite:///data/library.db
   ```

5. Create the data directory:
   ```bash
   mkdir -p data
   ```

6. Initialize the database:
   ```bash
   python run.py
   ```

### Running the Application

For development with database:
```bash
python run.py
```

For demo version (no database required):
```bash
python demo.py
```

Access the web interface at http://localhost:5002

## Demo Mode

The project includes a demo mode (`demo.py`) that showcases the UI and functionality without requiring a database connection. This is useful for:

- Quick preview of the application
- UI development and testing
- Demonstration purposes

To run the demo:
```bash
python demo.py
```

## Development Roadmap

See the [dev_log.md](dev_log.md) file for a detailed development roadmap and progress tracking.

## API Documentation

The Remixable Fiction Library provides a RESTful API for accessing and remixing content. Documentation will be available at `/api/docs` when running the application.

## Contributing

Contributions are welcome! Please see our contributing guidelines for more information.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Standard Ebooks](https://standardebooks.org/) for their high-quality, accessible ebook editions
- [Project Gutenberg](https://www.gutenberg.org/) for their vast collection of public domain works
- [Internet Archive](https://archive.org/) for preserving digital content
- [Wikisource](https://wikisource.org/) for their collaborative transcription efforts
- [Creative Commons](https://creativecommons.org/) for their open licensing framework
