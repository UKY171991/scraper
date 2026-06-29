from django.db import models

class Client(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class SearchEngine(models.Model):
    """Configure which search engines to use for scraping"""
    name = models.CharField(max_length=100, unique=True, help_text="Search engine name (e.g., Google, Bing)")
    is_active = models.BooleanField(default=True, help_text="Enable/disable this search engine")
    search_url_template = models.CharField(max_length=500, help_text="URL template with {query} placeholder")
    priority = models.IntegerField(default=1, help_text="Search order (1=highest priority)")
    add_reviews_keyword = models.BooleanField(default=True, help_text="Add 'reviews' to search query")
    max_results = models.IntegerField(default=10, help_text="Maximum results to fetch per search")
    delay_between_requests = models.FloatField(default=2.0, help_text="Delay in seconds between requests (avoid IP blocking)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'name']
        verbose_name = "Search Engine"
        verbose_name_plural = "Search Engines"

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({status}) - Priority {self.priority}"

class BlacklistedDomain(models.Model):
    """Domains to filter out during search-based scraping"""
    domain = models.CharField(max_length=255, unique=True, help_text="Domain to blacklist (e.g., birdeye.com, yelp.com)")
    category = models.CharField(max_length=100, blank=True, help_text="Category (e.g., Review Sites, Social Media)")
    reason = models.TextField(blank=True, help_text="Why this domain is blacklisted")
    is_active = models.BooleanField(default=True, help_text="Uncheck to temporarily disable this filter")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'domain']
        verbose_name = "Blacklisted Domain"
        verbose_name_plural = "Blacklisted Domains"

    def __str__(self):
        return f"{self.domain} ({self.category})"

class ScrapedData(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)
    category = models.CharField(max_length=255)
    city = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    link = models.URLField(max_length=500)  # Actual business website URL
    listing_url = models.URLField(max_length=500, blank=True, null=True)  # Reference URL from listing sites (Birdeye, Yelp, etc.)
    snippet = models.TextField(blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    is_elfsight = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.client})"
