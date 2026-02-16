from django.contrib import admin
from .models import Client, ScrapedData

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

@admin.register(ScrapedData)
class ScrapedDataAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'category', 'city', 'country', 'email', 'is_verified', 'phone', 'created_at')
    search_fields = ('title', 'category', 'city', 'country', 'link')
    list_filter = ('client', 'country', 'is_verified', 'created_at')

