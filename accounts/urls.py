from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", views.register_view, name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("staff/create/", views.create_staff_view, name="create_staff"),
    path("residents/", views.resident_management_view, name="residents"),
    path("staff/", views.staff_management_view, name="staff"),
]
