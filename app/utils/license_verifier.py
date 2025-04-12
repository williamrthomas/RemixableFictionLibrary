import re
import logging
from datetime import datetime
from pathlib import Path
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LicenseVerifier:
    """Utility for verifying the license status of works.
    
    This is a critical component for ensuring our library only contains
    properly licensed content that can be legally remixed.
    """
    
    def __init__(self, verification_db_path=None):
        """Initialize the license verifier.
        
        Args:
            verification_db_path: Path to store verification records
        """
        if verification_db_path:
            self.db_path = Path(verification_db_path)
        else:
            self.db_path = Path(__file__).parent.parent.parent / "data" / "metadata" / "license_verifications.json"
        
        # Create the directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing verifications if available
        if self.db_path.exists():
            with open(self.db_path, 'r') as f:
                self.verifications = json.load(f)
        else:
            self.verifications = {}
    
    def save_verifications(self):
        """Save the verification database to disk."""
        with open(self.db_path, 'w') as f:
            json.dump(self.verifications, f, indent=2)
    
    def verify_us_public_domain(self, publication_year, author_death_year=None):
        """Verify if a work is in the US public domain based on publication date.
        
        Args:
            publication_year: Year of first publication
            author_death_year: Year of author's death (optional)
            
        Returns:
            Dictionary with verification result and explanation
        """
        result = {
            'is_verified': False,
            'license_type': 'unknown',
            'confidence': 'low',
            'notes': []
        }
        
        # Check publication year for US public domain status
        if publication_year:
            try:
                year = int(publication_year)
                current_year = datetime.now().year
                
                # Works published before 1929 are in the US public domain as of 2024
                # This will need to be updated annually
                pd_cutoff_year = 1929  # For 2024-2025
                
                if year < pd_cutoff_year:
                    result['is_verified'] = True
                    result['license_type'] = 'US PD'
                    result['confidence'] = 'high'
                    result['notes'].append(f'Publication year {year} is before {pd_cutoff_year}, indicating US public domain status')
                else:
                    # Check for author death + 70 years rule
                    if author_death_year:
                        try:
                            death_year = int(author_death_year)
                            if current_year - death_year > 70:
                                result['is_verified'] = True
                                result['license_type'] = 'US PD'
                                result['confidence'] = 'medium'
                                result['notes'].append(f'Author died in {death_year}, which is more than 70 years ago')
                            else:
                                result['notes'].append(f'Author died in {death_year}, which is less than 70 years ago')
                        except ValueError:
                            result['notes'].append(f'Invalid author death year: {author_death_year}')
                    else:
                        result['notes'].append(f'Publication year {year} is after {pd_cutoff_year}, not in US public domain based on publication date')
            except ValueError:
                result['notes'].append(f'Invalid publication year: {publication_year}')
        else:
            result['notes'].append('No publication year provided')
        
        return result
    
    def verify_creative_commons(self, license_url):
        """Verify if a work has a valid Creative Commons license that permits remixing.
        
        Args:
            license_url: URL of the CC license
            
        Returns:
            Dictionary with verification result and explanation
        """
        result = {
            'is_verified': False,
            'license_type': 'unknown',
            'confidence': 'low',
            'notes': []
        }
        
        if not license_url:
            result['notes'].append('No license URL provided')
            return result
        
        # Check for CC0 (Public Domain Dedication)
        if 'creativecommons.org/publicdomain/zero' in license_url:
            result['is_verified'] = True
            result['license_type'] = 'CC0'
            result['confidence'] = 'high'
            result['notes'].append('CC0 Public Domain Dedication found')
        
        # Check for CC BY (Attribution)
        elif 'creativecommons.org/licenses/by/' in license_url and 'nd' not in license_url:
            result['is_verified'] = True
            result['license_type'] = 'CC BY'
            result['confidence'] = 'high'
            result['notes'].append('CC BY license found, which permits remixing with attribution')
        
        # Check for CC BY-SA (Attribution-ShareAlike)
        elif 'creativecommons.org/licenses/by-sa/' in license_url:
            result['is_verified'] = True
            result['license_type'] = 'CC BY-SA'
            result['confidence'] = 'high'
            result['notes'].append('CC BY-SA license found, which permits remixing with attribution and share-alike')
        
        # Check for non-remixable CC licenses
        elif 'creativecommons.org/licenses/' in license_url:
            if 'nd' in license_url:
                result['is_verified'] = False
                result['license_type'] = 'CC ND'
                result['confidence'] = 'high'
                result['notes'].append('CC license with NoDerivatives (ND) found, which does NOT permit remixing')
            elif 'nc' in license_url and 'nd' not in license_url:
                result['is_verified'] = False
                result['license_type'] = 'CC NC'
                result['confidence'] = 'high'
                result['notes'].append('CC license with NonCommercial (NC) found, which restricts commercial use')
        else:
            result['notes'].append(f'Unknown or unsupported license URL: {license_url}')
        
        return result
    
    def verify_project_gutenberg(self, pg_text):
        """Verify if a text from Project Gutenberg has been properly stripped of PG branding.
        
        Args:
            pg_text: Text content from Project Gutenberg
            
        Returns:
            Dictionary with verification result and explanation
        """
        result = {
            'is_verified': True,  # Assume it's verified until we find PG branding
            'license_type': 'US PD',
            'confidence': 'medium',
            'notes': []
        }
        
        # Common patterns for PG headers and footers
        pg_patterns = [
            r"The Project Gutenberg",
            r"Project Gutenberg",
            r"Gutenberg",
            r"This eBook is for the use of anyone anywhere",
            r"This etext was prepared by",
            r"End of the Project Gutenberg EBook",
            r"End of Project Gutenberg's",
            r"This file should be named",
            r"This and all associated files"
        ]
        
        for pattern in pg_patterns:
            if re.search(pattern, pg_text, re.IGNORECASE):
                result['is_verified'] = False
                result['notes'].append(f'Project Gutenberg branding found: "{pattern}"')
        
        if result['is_verified']:
            result['notes'].append('No Project Gutenberg branding found')
            result['confidence'] = 'high'
        
        return result
    
    def record_verification(self, source, item_id, verification_result, verified_by=None):
        """Record a license verification in the database.
        
        Args:
            source: Source of the work (standard_ebooks, project_gutenberg, etc.)
            item_id: Identifier for the work
            verification_result: Result of verification
            verified_by: User ID who performed the verification
            
        Returns:
            Updated verification record
        """
        key = f"{source}:{item_id}"
        
        verification_record = {
            'source': source,
            'item_id': item_id,
            'verification_result': verification_result,
            'verified_by': verified_by,
            'verified_at': datetime.now().isoformat(),
            'history': []
        }
        
        # If we already have a record, add the current one to history
        if key in self.verifications:
            old_record = self.verifications[key]
            if 'history' not in old_record:
                old_record['history'] = []
            
            # Move the current record to history
            history_item = {
                'verification_result': old_record['verification_result'],
                'verified_by': old_record['verified_by'],
                'verified_at': old_record['verified_at']
            }
            old_record['history'].append(history_item)
            
            # Update with new verification
            verification_record['history'] = old_record['history']
        
        # Save the new record
        self.verifications[key] = verification_record
        self.save_verifications()
        
        return verification_record
    
    def get_verification(self, source, item_id):
        """Get a verification record from the database.
        
        Args:
            source: Source of the work
            item_id: Identifier for the work
            
        Returns:
            Verification record if found, None otherwise
        """
        key = f"{source}:{item_id}"
        return self.verifications.get(key)
    
    def is_verified_remixable(self, source, item_id):
        """Check if a work has been verified as remixable.
        
        Args:
            source: Source of the work
            item_id: Identifier for the work
            
        Returns:
            Boolean indicating if the work is verified as remixable
        """
        verification = self.get_verification(source, item_id)
        
        if not verification:
            return False
        
        result = verification.get('verification_result', {})
        
        # Check if it's verified and has a remixable license
        if result.get('is_verified', False):
            license_type = result.get('license_type', 'unknown')
            
            # These license types permit remixing
            remixable_licenses = ['US PD', 'CC0', 'CC BY', 'CC BY-SA']
            
            return license_type in remixable_licenses
        
        return False
