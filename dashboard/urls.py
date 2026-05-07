from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("contact/", views.contact_view, name="contact"),
    path("privacy-policy/", views.privacy_policy_view, name="privacy_policy"),
    path("terms/", views.terms_view, name="terms"),
    path("resident/", views.resident_dashboard_view, name="resident"),
    path("resident/help/", views.resident_help_view, name="resident_help"),
    path("staff/", views.staff_dashboard_view, name="staff"),
    path("admin-dashboard/", views.admin_dashboard_view, name="admin"),
]
