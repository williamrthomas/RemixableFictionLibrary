# Changelog

All notable changes to the Remixable Fiction Library project will be documented in this file.

## [0.5.0] - 2025-04-12

### Added
- Initial public release
- Blueprint architecture for improved code organization
- Open access system with no login required for browsing content
- Basic content browsing and reading functionality
- License verification workflow
- Admin-only import functionality
- Public API endpoints for content discovery
- Public import request system

### Fixed
- Database initialization issue with SQLite path format
- Template errors related to user authentication checks
- Routing issues with blueprint implementation

### Changed
- Refactored routes into three main blueprints (main, auth, api)
- Updated templates to use blueprint routes consistently
- Improved error handling and logging
- Changed server port from 5000 to 5002
