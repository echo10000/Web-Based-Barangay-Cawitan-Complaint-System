from django.urls import path

from . import views

app_name = "complaints"

urlpatterns = [
    path("", views.complaint_list_view, name="list"),
    path("submit/", views.submit_complaint_view, name="submit"),
    path("<int:pk>/", views.complaint_detail_view, name="detail"),
    path("<int:pk>/update/", views.update_complaint_view, name="update"),
    path("<int:pk>/delete/", views.delete_complaint_view, name="delete"),
    path("reports/", views.reports_view, name="reports"),
]
