from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render

from accounts.models import User
from complaints.models import Complaint, Notification


@login_required
def home_view(request):
    if request.user.is_barangay_admin:
        return redirect("dashboard:admin")
    if request.user.is_staff_member:
        return redirect("dashboard:staff")
    return redirect("dashboard:resident")


@login_required
def resident_dashboard_view(request):
    if not request.user.is_resident:
        messages.error(request, "Residents only.")
        return redirect("dashboard:home")
    complaints = Complaint.objects.filter(resident=request.user)
    notifications = Notification.objects.filter(user=request.user)[:5]
    return render(
        request,
        "dashboard/resident_dashboard.html",
        {
            "total_complaints": complaints.count(),
            "pending_count": complaints.filter(status=Complaint.Status.PENDING).count(),
            "resolved_count": complaints.filter(status=Complaint.Status.RESOLVED).count(),
            "recent_complaints": complaints[:5],
            "notifications": notifications,
        },
    )


@login_required
def staff_dashboard_view(request):
    if not request.user.is_staff_member:
        messages.error(request, "Staff only.")
        return redirect("dashboard:home")
    complaints = Complaint.objects.filter(assigned_to=request.user)
    return render(
        request,
        "dashboard/staff_dashboard.html",
        {
            "assigned_count": complaints.count(),
            "in_progress_count": complaints.filter(status=Complaint.Status.IN_PROGRESS).count(),
            "resolved_count": complaints.filter(status=Complaint.Status.RESOLVED).count(),
            "recent_complaints": complaints[:8],
        },
    )


@login_required
def admin_dashboard_view(request):
    if not request.user.is_barangay_admin:
        messages.error(request, "Admins only.")
        return redirect("dashboard:home")
    status_counts = Complaint.objects.values("status").annotate(total=Count("id"))
    return render(
        request,
        "dashboard/admin_dashboard.html",
        {
            "total_complaints": Complaint.objects.count(),
            "pending_count": Complaint.objects.filter(status=Complaint.Status.PENDING).count(),
            "resolved_count": Complaint.objects.filter(status=Complaint.Status.RESOLVED).count(),
            "resident_count": User.objects.filter(role=User.Role.RESIDENT).count(),
            "staff_count": User.objects.filter(role=User.Role.STAFF).count(),
            "status_counts": status_counts,
            "recent_complaints": Complaint.objects.select_related("resident", "assigned_to")[:8],
        },
    )
