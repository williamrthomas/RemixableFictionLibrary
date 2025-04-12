from .. import db

class License(db.Model):
    """Model for content licenses."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    short_name = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)
    url = db.Column(db.String(255))
    
    # License properties
    allows_remix = db.Column(db.Boolean, default=True)
    requires_attribution = db.Column(db.Boolean, default=False)
    share_alike = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<License {self.name}>'
    
    @classmethod
    def seed_default_licenses(cls, db_session):
        """Seed the database with default license types."""
        default_licenses = [
            {
                'name': 'Public Domain (US)',
                'short_name': 'PD-US',
                'description': 'Works in the US public domain (published before 1929). No copyright restrictions in the US.',
                'url': 'https://en.wikipedia.org/wiki/Public_domain_in_the_United_States',
                'allows_remix': True,
                'requires_attribution': False,
                'share_alike': False
            },
            {
                'name': 'Creative Commons Zero (CC0)',
                'short_name': 'CC0',
                'description': 'Creative Commons Zero - Public Domain Dedication. No rights reserved.',
                'url': 'https://creativecommons.org/publicdomain/zero/1.0/',
                'allows_remix': True,
                'requires_attribution': False,
                'share_alike': False
            },
            {
                'name': 'Creative Commons Attribution (CC BY)',
                'short_name': 'CC-BY',
                'description': 'Creative Commons Attribution. Allows remix with attribution.',
                'url': 'https://creativecommons.org/licenses/by/4.0/',
                'allows_remix': True,
                'requires_attribution': True,
                'share_alike': False
            },
            {
                'name': 'Creative Commons Attribution-ShareAlike (CC BY-SA)',
                'short_name': 'CC-BY-SA',
                'description': 'Creative Commons Attribution-ShareAlike. Allows remix with attribution, derivatives must use same license.',
                'url': 'https://creativecommons.org/licenses/by-sa/4.0/',
                'allows_remix': True,
                'requires_attribution': True,
                'share_alike': True
            },
            {
                'name': 'Project Gutenberg License',
                'short_name': 'PG',
                'description': 'Project Gutenberg License. US public domain text with trademark restrictions.',
                'url': 'https://www.gutenberg.org/policy/license.html',
                'allows_remix': True,
                'requires_attribution': False,
                'share_alike': False
            }
        ]
        
        for license_data in default_licenses:
            existing = cls.query.filter_by(short_name=license_data['short_name']).first()
            if not existing:
                new_license = cls(**license_data)
                db_session.add(new_license)
        
        db_session.commit()
