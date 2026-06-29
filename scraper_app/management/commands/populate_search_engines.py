from django.core.management.base import BaseCommand
from scraper_app.models import SearchEngine


class Command(BaseCommand):
    help = 'Populate the database with default search engines'

    def handle(self, *args, **options):
        engines = [
            {
                'name': 'Google',
                'search_url_template': 'https://www.google.com/search?q={query}&hl=en&lr=lang_en',
                'priority': 1,
                'add_reviews_keyword': True,
                'is_active': True,
                'max_results': 50,  # Increased to 50
                'delay_between_requests': 3.0  # 3 seconds to avoid blocking
            },
            {
                'name': 'Bing',
                'search_url_template': 'https://www.bing.com/search?q={query}&setlang=en',
                'priority': 2,
                'add_reviews_keyword': True,
                'is_active': True,
                'max_results': 50,  # Increased to 50
                'delay_between_requests': 2.0  # 2 seconds
            },
            {
                'name': 'DuckDuckGo',
                'search_url_template': 'https://html.duckduckgo.com/html/?q={query}',
                'priority': 3,
                'add_reviews_keyword': False,
                'is_active': False,  # Disabled by default (connection issues)
                'max_results': 30,
                'delay_between_requests': 2.0
            },
        ]

        created_count = 0
        updated_count = 0
        
        for engine_data in engines:
            obj, created = SearchEngine.objects.update_or_create(
                name=engine_data['name'],
                defaults={
                    'search_url_template': engine_data['search_url_template'],
                    'priority': engine_data['priority'],
                    'add_reviews_keyword': engine_data['add_reviews_keyword'],
                    'is_active': engine_data['is_active'],
                    'max_results': engine_data['max_results'],
                    'delay_between_requests': engine_data['delay_between_requests']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {engine_data["name"]}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'→ Updated: {engine_data["name"]}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nSummary:'))
        self.stdout.write(self.style.SUCCESS(f'  Created: {created_count} search engines'))
        self.stdout.write(self.style.SUCCESS(f'  Updated: {updated_count} search engines'))
        self.stdout.write(self.style.SUCCESS(f'  Total: {created_count + updated_count} search engines'))
