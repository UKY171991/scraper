from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('scrape/', views.scrape_data, name='scrape'),
    path('download/', views.download_csv, name='download'),
]
