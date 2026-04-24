from django.urls import path
from . import views

app_name = 'complaints'

urlpatterns = [
    # Public URLs
    path('', views.index, name='index'),
    path('file/', views.file_complaint, name='file_complaint'),
    path('complaints/', views.complaint_list, name='complaint_list'),
    path('complaint/<int:pk>/', views.complaint_detail, name='complaint_detail'),
    path('track/', views.track_complaint, name='track_complaint'),
    
    # User URLs (requires login)
    path('my-complaints/', views.my_complaints, name='my_complaints'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Staff URLs (requires login + staff)
    path('staff-dashboard/', views.staff_dashboard, name='staff_dashboard'),
    
    # API endpoints
    path('api/categories/', views.api_categories, name='api_categories'),
    path('api/stats/', views.api_complaint_stats, name='api_stats'),
]