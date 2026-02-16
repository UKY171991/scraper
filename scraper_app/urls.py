from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('scrape/', views.scrape_data, name='scrape'),
    path('download/', views.download_csv, name='download'),
    path('download/<int:client_id>/', views.download_client_csv, name='download_client'),
]
