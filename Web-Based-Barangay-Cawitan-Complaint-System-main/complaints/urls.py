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
    path('staff/complaints/', views.staff_complaint_list, name='staff_complaint_list'),
    path('staff/complaint/<int:pk>/edit/', views.staff_edit_complaint, name='staff_edit_complaint'),
    path('staff/complaint/<int:pk>/update/', views.staff_add_update, name='staff_add_update'),
    path('staff/reports/', views.staff_reports, name='staff_reports'),
    path('staff/my-complaints/', views.staff_my_complaints, name='staff_my_complaints'),
    
    # API endpoints
    path('api/categories/', views.api_categories, name='api_categories'),
    path('api/stats/', views.api_complaint_stats, name='api_stats'),
]