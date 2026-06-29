from django.contrib import admin
from .models import Client, ScrapedData, BlacklistedDomain, SearchEngine

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

@admin.register(SearchEngine)
class SearchEngineAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'priority', 'max_results', 'delay_between_requests', 'add_reviews_keyword')
    list_filter = ('is_active', 'add_reviews_keyword')
    search_fields = ('name', 'search_url_template')
    list_editable = ('is_active', 'priority', 'delay_between_requests')
    ordering = ('priority', 'name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active', 'priority')
        }),
        ('Search Configuration', {
            'fields': ('search_url_template', 'add_reviews_keyword', 'max_results'),
            'description': 'Use {query} as placeholder in URL template. Example: https://www.google.com/search?q={query}&hl=en'
        }),
        ('Anti-Blocking Settings', {
            'fields': ('delay_between_requests',),
            'description': 'Increase delay to avoid IP blocking. Recommended: 2-5 seconds'
        }),
    )
    
    actions = ['activate_engines', 'deactivate_engines']
    
    def activate_engines(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} search engine(s) activated.')
    activate_engines.short_description = "Activate selected search engines"
    
    def deactivate_engines(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} search engine(s) deactivated.')
    deactivate_engines.short_description = "Deactivate selected search engines"

@admin.register(BlacklistedDomain)
class BlacklistedDomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'category', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('domain', 'category', 'reason')
    list_editable = ('is_active',)
    ordering = ('category', 'domain')
    
    fieldsets = (
        ('Domain Information', {
            'fields': ('domain', 'category', 'is_active')
        }),
        ('Details', {
            'fields': ('reason',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_domains', 'deactivate_domains']
    
    def activate_domains(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} domain(s) activated.')
    activate_domains.short_description = "Activate selected domains"
    
    def deactivate_domains(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} domain(s) deactivated.')
    deactivate_domains.short_description = "Deactivate selected domains"

@admin.register(ScrapedData)
class ScrapedDataAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'category', 'city', 'country', 'email', 'is_verified', 'phone', 'created_at')
    search_fields = ('title', 'category', 'city', 'country', 'link')
    list_filter = ('client', 'country', 'is_verified', 'created_at')
    ordering = ('is_verified', '-created_at')
