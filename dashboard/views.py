import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.expressions import RawSQL
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import StaffProfile, User
from complaints.models import Complaint, Notification


def home_view(request):
    if not request.user.is_authenticated:
        return render(request, "dashboard/landing.html")
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

    # Profile completion — 5 fields, each worth 20 %
    profile_fields = [request.user.first_name, request.user.last_name, request.user.email]
    try:
        p = request.user.resident_profile
        profile_fields.append(p.phone_number)
        profile_fields.append(p.address)
    except Exception:
        profile_fields.extend(["", ""])
    profile_completion = int(sum(1 for f in profile_fields if f) / len(profile_fields) * 100)

    return render(
        request,
        "dashboard/resident_dashboard.html",
        {
            "total_complaints": complaints.count(),
            "pending_count": complaints.filter(status=Complaint.Status.PENDING).count(),
            "resolved_count": complaints.filter(status=Complaint.Status.RESOLVED).count(),
            "recent_complaints": complaints[:5],
            "notifications": notifications,
            "profile_completion": profile_completion,
        },
    )


@login_required
def staff_dashboard_view(request):
    if not request.user.is_staff_member:
        messages.error(request, "Staff only.")
        return redirect("dashboard:home")
    StaffProfile.objects.get_or_create(user=request.user)
    complaints = Complaint.objects.filter(
        Q(assigned_to=request.user) | Q(assigned_to__isnull=True)
    ).select_related("resident", "assigned_to", "category")
    pending_count = complaints.filter(status=Complaint.Status.PENDING).count()
    under_review_count = complaints.filter(status=Complaint.Status.UNDER_REVIEW).count()
    in_progress_count = complaints.filter(status=Complaint.Status.IN_PROGRESS).count()
    resolved_count = complaints.filter(status=Complaint.Status.RESOLVED).count()
    urgent_assigned = complaints.filter(
        status__in=[Complaint.Status.PENDING, Complaint.Status.UNDER_REVIEW],
        created_at__lt=timezone.now() - timedelta(days=3),
    )[:5]
    return render(
        request,
        "dashboard/staff_dashboard.html",
        {
            "assigned_count": complaints.count(),
            "needs_review_count": pending_count + under_review_count,
            "pending_count": pending_count,
            "under_review_count": under_review_count,
            "in_progress_count": in_progress_count,
            "resolved_count": resolved_count,
            "urgent_assigned": urgent_assigned,
            "recent_complaints": complaints[:8],
        },
    )


@login_required
def admin_dashboard_view(request):
    if not request.user.is_barangay_admin:
        messages.error(request, "Admins only.")
        return redirect("dashboard:home")
    now              = timezone.now()
    urgent_threshold = now - timedelta(days=3)

    # ── Counts ────────────────────────────────────────
    pending_count     = Complaint.objects.filter(status=Complaint.Status.PENDING).count()
    under_review_count= Complaint.objects.filter(status=Complaint.Status.UNDER_REVIEW).count()
    in_progress_count = Complaint.objects.filter(status=Complaint.Status.IN_PROGRESS).count()
    resolved_count    = Complaint.objects.filter(status=Complaint.Status.RESOLVED).count()
    rejected_count    = Complaint.objects.filter(status=Complaint.Status.REJECTED).count()
    urgent_count      = Complaint.objects.filter(
                            status=Complaint.Status.PENDING,
                            created_at__lt=urgent_threshold,
                        ).count()

    # ── Chart 1 — Complaints by Status ────────────────
    chart_status = {
        "labels": ["Pending", "Under Review", "In Progress", "Resolved", "Rejected"],
        "data":   [pending_count, under_review_count, in_progress_count, resolved_count, rejected_count],
    }

    # ── Chart 2 — Complaints by Category ──────────────
    cat_qs = (
        Complaint.objects
        .values("category__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )
    chart_category = {
        "labels": [r["category__name"] or "Uncategorized" for r in cat_qs],
        "data":   [r["total"] for r in cat_qs],
    }

    # ── Chart 3 — Monthly Complaints (last 12 months) ─
    # RawSQL avoids TruncMonth's requirement for MySQL timezone tables (not
    # installed on typical XAMPP/MariaDB setups).
    monthly_qs = (
        Complaint.objects
        .filter(created_at__gte=now - timedelta(days=365))
        .annotate(month_str=RawSQL("DATE_FORMAT(created_at, '%%Y-%%m')", []))
        .values("month_str")
        .annotate(total=Count("id"))
        .order_by("month_str")
    )
    monthly_dict = {item["month_str"]: item["total"] for item in monthly_qs}

    monthly_labels, monthly_data = [], []
    for i in range(11, -1, -1):
        total_m = now.month - 1 - i
        yr  = now.year + total_m // 12
        mo  = total_m % 12 + 1
        key = f"{yr:04d}-{mo:02d}"
        monthly_labels.append(datetime(yr, mo, 1).strftime("%b %Y"))
        monthly_data.append(monthly_dict.get(key, 0))

    chart_monthly = {"labels": monthly_labels, "data": monthly_data}

    # ── Chart 4 — Urgent Complaints list ──────────────
    urgent_complaints = (
        Complaint.objects
        .filter(status=Complaint.Status.PENDING, created_at__lt=urgent_threshold)
        .select_related("resident", "category")
        .order_by("created_at")[:6]
    )

    return render(
        request,
        "dashboard/admin_dashboard.html",
        {
            "total_complaints":   Complaint.objects.count(),
            "pending_count":      pending_count,
            "in_progress_count":  in_progress_count,
            "resolved_count":     resolved_count,
            "urgent_count":       urgent_count,
            "resident_count":     User.objects.filter(role=User.Role.RESIDENT).count(),
            "staff_count":        User.objects.filter(role=User.Role.STAFF).count(),
            "recent_complaints":  Complaint.objects.select_related("resident", "assigned_to")[:8],
            "urgent_complaints":  urgent_complaints,
            "chart_status":       json.dumps(chart_status),
            "chart_category":     json.dumps(chart_category),
            "chart_monthly":      json.dumps(chart_monthly),
        },
    )
