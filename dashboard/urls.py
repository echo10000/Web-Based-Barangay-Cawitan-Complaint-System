from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("resident/", views.resident_dashboard_view, name="resident"),
    path("resident/help/", views.resident_help_view, name="resident_help"),
    path("staff/", views.staff_dashboard_view, name="staff"),
    path("admin-dashboard/", views.admin_dashboard_view, name="admin"),
]
