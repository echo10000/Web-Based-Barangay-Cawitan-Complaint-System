from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("set-new-password/", views.set_new_password_view, name="set_new_password"),
    path("profile/", views.profile_view, name="profile"),
    path("<int:pk>/edit/", views.edit_account_view, name="edit_account"),
    path("<int:pk>/toggle-status/", views.toggle_account_status_view, name="toggle_account_status"),
    path("<int:pk>/reset-password/", views.reset_account_password_view, name="reset_account_password"),
    path("<int:pk>/verify-resident/", views.verify_resident_view, name="verify_resident"),
    path("<int:pk>/resident-id/<str:side>/", views.resident_id_file_view, name="resident_id_file"),
    path("staff/create/", views.create_staff_view, name="create_staff"),
    path("residents/", views.resident_management_view, name="residents"),
    path("staff/", views.staff_management_view, name="staff"),
]
