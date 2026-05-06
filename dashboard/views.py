import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, Count, IntegerField, Q, When
from django.db.models.expressions import RawSQL
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import StaffProfile, User
from complaints.models import Complaint, ComplaintCategory, Notification
from complaints.services import create_notification


ACTIVE_URGENT_STATUSES = [
    Complaint.Status.PENDING,
    Complaint.Status.UNDER_REVIEW,
    Complaint.Status.RESPONDENT_NOT_CONTACTED,
    Complaint.Status.RESPONDENT_CONTACTED,
    Complaint.Status.WAITING_RESPONDENT_RESPONSE,
    Complaint.Status.RESPONDENT_RESPONSE_RECORDED,
    Complaint.Status.NO_RESPONSE,
    Complaint.Status.FAILED_TO_ATTEND,
    Complaint.Status.SECOND_NOTICE_SENT,
    Complaint.Status.HEARING_SCHEDULED,
    Complaint.Status.IN_MEDIATION,
    Complaint.Status.IN_PROGRESS,
]

URGENT_PRIORITY_ORDER = Case(
    When(priority=Complaint.Priority.URGENT, then=0),
    default=1,
    output_field=IntegerField(),
)


def notify_admins_about_overdue_complaints(overdue_complaints):
    admins = User.objects.filter(Q(role=User.Role.ADMIN) | Q(is_superuser=True)).distinct()
    for complaint in overdue_complaints:
        message = f"Complaint '{complaint.title}' is overdue for SLA response."
        for admin in admins:
            create_notification(
                user=admin,
                complaint=complaint,
                message=message,
                notification_type=Notification.Type.OVERDUE,
                dedupe=True,
            )


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
    resident_profile = getattr(request.user, "resident_profile", None)

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
            "resident_profile": resident_profile,
        },
    )


@login_required
def resident_help_view(request):
    if not request.user.is_resident:
        messages.error(request, "Residents only.")
        return redirect("dashboard:home")

    categories = ComplaintCategory.objects.filter(is_active=True).order_by("name")
    if not categories.exists():
        categories = [
            {
                "name": "Noise Complaint",
                "description": "Loud music, disturbance, or repeated neighborhood noise.",
                "default_priority": "NORMAL",
                "target_resolution_hours": 72,
                "responsible_department": "Barangay Desk",
            },
            {
                "name": "Garbage & Sanitation",
                "description": "Waste collection, cleanliness, drainage odor, or sanitation concerns.",
                "default_priority": "NORMAL",
                "target_resolution_hours": 72,
                "responsible_department": "Sanitation",
            },
            {
                "name": "Road, Lighting, or Obstruction",
                "description": "Street lighting, road hazards, blocked pathways, or drainage issues.",
                "default_priority": "HIGH",
                "target_resolution_hours": 48,
                "responsible_department": "Public Works",
            },
            {
                "name": "Safety & Security",
                "description": "Public safety concerns that need barangay attention.",
                "default_priority": "URGENT",
                "target_resolution_hours": 24,
                "responsible_department": "Barangay Tanod",
            },
        ]

    now = timezone.localtime()
    is_open_now = now.weekday() < 5 and 8 <= now.hour < 17

    return render(
        request,
        "dashboard/resident_help.html",
        {
            "categories": categories,
            "is_open_now": is_open_now,
        },
    )


@login_required
def staff_dashboard_view(request):
    if not request.user.is_staff_member:
        messages.error(request, "Staff only.")
        return redirect("dashboard:home")
    StaffProfile.objects.get_or_create(user=request.user)
    active_statuses = ACTIVE_URGENT_STATUSES
    complaints = Complaint.objects.filter(
        Q(assigned_to=request.user) | Q(assigned_to__isnull=True)
    ).select_related("resident", "assigned_to", "category")
    assigned_to_me = complaints.filter(assigned_to=request.user)
    unassigned_complaints = complaints.filter(assigned_to__isnull=True, status__in=active_statuses).order_by("deadline_at", "created_at")
    overdue_complaints = assigned_to_me.filter(status__in=active_statuses, deadline_at__lt=timezone.now()).order_by("deadline_at")
    recently_updated = assigned_to_me.order_by("-updated_at")
    pending_count = complaints.filter(status=Complaint.Status.PENDING).count()
    under_review_count = complaints.filter(status=Complaint.Status.UNDER_REVIEW).count()
    in_progress_count = complaints.filter(status=Complaint.Status.IN_PROGRESS).count()
    resolved_count = complaints.filter(status=Complaint.Status.RESOLVED).count()
    urgent_filter = Q(priority=Complaint.Priority.URGENT) | Q(deadline_at__lt=timezone.now())
    urgent_assigned = complaints.filter(
        urgent_filter,
        status__in=ACTIVE_URGENT_STATUSES,
    ).annotate(urgent_priority_order=URGENT_PRIORITY_ORDER).order_by("urgent_priority_order", "created_at")[:5]
    return render(
        request,
        "dashboard/staff_dashboard.html",
        {
            "assigned_count": assigned_to_me.count(),
            "unassigned_count": unassigned_complaints.count(),
            "overdue_count": overdue_complaints.count(),
            "needs_review_count": pending_count + under_review_count,
            "pending_count": pending_count,
            "under_review_count": under_review_count,
            "in_progress_count": in_progress_count,
            "resolved_count": resolved_count,
            "urgent_assigned": urgent_assigned,
            "unassigned_complaints": unassigned_complaints[:5],
            "assigned_to_me_complaints": assigned_to_me[:6],
            "overdue_complaints": overdue_complaints[:5],
            "recently_updated_complaints": recently_updated[:5],
            "recent_complaints": assigned_to_me[:8],
        },
    )


@login_required
def admin_dashboard_view(request):
    if not request.user.is_barangay_admin:
        messages.error(request, "Admins only.")
        return redirect("dashboard:home")
    now              = timezone.now()

    # ── Counts ────────────────────────────────────────
    pending_count     = Complaint.objects.filter(status=Complaint.Status.PENDING).count()
    under_review_count= Complaint.objects.filter(status=Complaint.Status.UNDER_REVIEW).count()
    in_progress_count = Complaint.objects.filter(status=Complaint.Status.IN_PROGRESS).count()
    resolved_count    = Complaint.objects.filter(status=Complaint.Status.RESOLVED).count()
    rejected_count    = Complaint.objects.filter(status=Complaint.Status.REJECTED).count()
    urgent_filter     = Q(priority=Complaint.Priority.URGENT) | Q(deadline_at__lt=now)
    urgent_count      = Complaint.objects.filter(
                            urgent_filter,
                            status__in=ACTIVE_URGENT_STATUSES,
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
        .filter(urgent_filter, status__in=ACTIVE_URGENT_STATUSES)
        .select_related("resident", "category")
        .annotate(urgent_priority_order=URGENT_PRIORITY_ORDER)
        .order_by("urgent_priority_order", "created_at")[:6]
    )
    overdue_complaints = Complaint.objects.filter(
        deadline_at__lt=now,
        status__in=ACTIVE_URGENT_STATUSES,
    ).only("id", "title")
    notify_admins_about_overdue_complaints(overdue_complaints)

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
