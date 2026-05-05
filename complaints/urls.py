from django.urls import path

from . import views

app_name = "complaints"

urlpatterns = [
    path("", views.complaint_list_view, name="list"),
    path("submit/", views.submit_complaint_view, name="submit"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read_view, name="mark_all_notifications_read"),
    path("<int:pk>/", views.complaint_detail_view, name="detail"),
    path("<int:pk>/update/", views.update_complaint_view, name="update"),
    path("<int:pk>/delete/", views.delete_complaint_view, name="delete"),
    path("reports/", views.reports_view, name="reports"),
]
