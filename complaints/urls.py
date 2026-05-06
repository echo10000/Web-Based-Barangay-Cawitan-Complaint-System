from django.urls import path

from . import views

app_name = "complaints"

urlpatterns = [
    path("", views.complaint_list_view, name="list"),
    path("submit/", views.submit_complaint_view, name="submit"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read_view, name="mark_all_notifications_read"),
    path("notifications/<int:pk>/view/", views.notification_view_redirect, name="notification_view"),
    path("<int:pk>/", views.complaint_detail_view, name="detail"),
    path("<int:pk>/update/", views.update_complaint_view, name="update"),
    path("<int:pk>/delete/", views.delete_complaint_view, name="delete"),
    path("reports/", views.reports_view, name="reports"),
    path("reports/export/csv/", views.reports_export_csv_view, name="reports_export_csv"),
    path("reports/export/pdf/", views.reports_export_pdf_view, name="reports_export_pdf"),
    path("categories/", views.category_management_view, name="categories"),
    path("categories/create/", views.category_create_view, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_edit_view, name="category_edit"),
    path("categories/<int:pk>/toggle/", views.category_toggle_view, name="category_toggle"),
]
