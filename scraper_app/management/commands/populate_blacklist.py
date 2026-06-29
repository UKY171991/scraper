from django.core.management.base import BaseCommand
from scraper_app.models import BlacklistedDomain


class Command(BaseCommand):
    help = 'Populate the database with default blacklisted domains'

    def handle(self, *args, **options):
        domains = [
            # Review & Listing Sites
            ('birdeye.com', 'Review Sites', 'Review aggregator'),
            ('trustpilot.com', 'Review Sites', 'Review platform'),
            ('yelp.com', 'Review Sites', 'Business reviews'),
            ('yellowpages.', 'Directories', 'Business directory'),
            ('tripadvisor.', 'Review Sites', 'Travel reviews'),
            ('bbb.org', 'Review Sites', 'Better Business Bureau'),
            ('foursquare.com', 'Review Sites', 'Location reviews'),
            ('zomato.com', 'Review Sites', 'Restaurant reviews'),
            ('clutch.co', 'Business Listings', 'B2B reviews'),
            ('goodfirms.co', 'Business Listings', 'IT company reviews'),
            ('yably.ca', 'Directories', 'Canadian business directory'),
            ('bestratedintoronto.com', 'Directories', 'Toronto business listings'),
            ('threebestrated.', 'Directories', 'Top 3 business listings'),
            ('threebest.', 'Directories', 'Top 3 business listings'),
            ('3bestrated.', 'Directories', 'Top 3 business listings'),
            
            # Legal Directories
            ('lawyers.com', 'Legal Directories', 'Lawyer directory'),
            ('avvo.com', 'Legal Directories', 'Lawyer ratings'),
            ('findlaw.com', 'Legal Directories', 'Legal resources'),
            ('martindale.com', 'Legal Directories', 'Lawyer directory'),
            ('superlawyers.com', 'Legal Directories', 'Top lawyer listings'),
            ('nolo.com', 'Legal Directories', 'Legal information'),
            ('bestlawfirms.com', 'Legal Directories', 'Law firm rankings'),
            ('lexpert.ca', 'Legal Directories', 'Canadian lawyer directory'),
            
            # Social Media
            ('facebook.com', 'Social Media', 'Social network'),
            ('instagram.com', 'Social Media', 'Photo sharing'),
            ('twitter.com', 'Social Media', 'Microblogging'),
            ('linkedin.com', 'Social Media', 'Professional network'),
            ('reddit.com', 'Social Media', 'Discussion forum'),
            ('quora.com', 'Social Media', 'Q&A platform'),
            ('pinterest.com', 'Social Media', 'Image sharing'),
            ('youtube.com', 'Social Media', 'Video platform'),
            ('tumblr.com', 'Social Media', 'Blogging platform'),
            ('medium.com', 'Social Media', 'Publishing platform'),
            
            # Maps & Directories
            ('google.com/maps', 'Maps', 'Google Maps'),
            ('maps.google.com', 'Maps', 'Google Maps'),
            ('mapquest.com', 'Maps', 'Map service'),
            ('justdial.com', 'Directories', 'Indian business directory'),
            ('indiamart.com', 'Directories', 'Indian B2B marketplace'),
            ('sulekha.com', 'Directories', 'Indian classifieds'),
            ('indiatimes.com', 'News', 'News portal'),
            ('magicpin.in', 'Directories', 'Local discovery'),
            ('urbanpro.com', 'Directories', 'Service provider directory'),
            ('timesofindia.', 'News', 'News portal'),
            
            # Job Sites
            ('glassdoor.', 'Job Sites', 'Company reviews'),
            ('indeed.com', 'Job Sites', 'Job search'),
            
            # Travel & Booking
            ('booking.com', 'Travel', 'Hotel booking'),
            ('expedia.', 'Travel', 'Travel booking'),
            ('hotels.com', 'Travel', 'Hotel booking'),
            ('airbnb.com', 'Travel', 'Vacation rentals'),
            ('opentable.com', 'Travel', 'Restaurant reservations'),
            ('urbanspoon.com', 'Travel', 'Restaurant reviews'),
            
            # Home Services
            ('homeadvisor.com', 'Home Services', 'Contractor directory'),
            ('angi.com', 'Home Services', 'Service provider directory'),
            ('thumbtack.com', 'Home Services', 'Service marketplace'),
            ('houzz.com', 'Home Services', 'Home design'),
            ('porch.com', 'Home Services', 'Home improvement'),
            ('bark.com', 'Home Services', 'Service marketplace'),
            
            # Other
            ('wikipedia.org', 'Reference', 'Encyclopedia'),
            ('zumba.com', 'Fitness', 'Fitness classes'),
            
            # Search Engines
            ('search.yahoo.com', 'Search Engines', 'Yahoo search'),
            ('search.brave.com', 'Search Engines', 'Brave search'),
            
            # Government & Education
            ('.gov', 'Government', 'Government sites'),
            ('.nic.in', 'Government', 'Indian government'),
            ('gov.in', 'Government', 'Indian government'),
            ('gov.uk', 'Government', 'UK government'),
            ('usa.gov', 'Government', 'US government'),
            ('pib.gov.in', 'Government', 'Indian government'),
            ('.edu', 'Education', 'Educational institutions'),
            ('.mil', 'Government', 'Military sites'),
            ('india.gov.in', 'Government', 'Indian government'),
        ]

        created_count = 0
        updated_count = 0
        
        for domain, category, reason in domains:
            obj, created = BlacklistedDomain.objects.get_or_create(
                domain=domain,
                defaults={
                    'category': category,
                    'reason': reason,
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {domain}'))
            else:
                # Update existing
                obj.category = category
                obj.reason = reason
                obj.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'→ Updated: {domain}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nSummary:'))
        self.stdout.write(self.style.SUCCESS(f'  Created: {created_count} domains'))
        self.stdout.write(self.style.SUCCESS(f'  Updated: {updated_count} domains'))
        self.stdout.write(self.style.SUCCESS(f'  Total: {created_count + updated_count} domains'))
