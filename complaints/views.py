from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from .forms import ComplaintForm, ComplaintUpdateForm
from .models import Complaint, ComplaintResponse, ComplaintStatusHistory, Notification, UploadedEvidence


ACTIVE_ASSIGNMENT_STATUSES = [
    Complaint.Status.PENDING,
    Complaint.Status.UNDER_REVIEW,
    Complaint.Status.IN_PROGRESS,
]


def staff_or_admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_staff_member or request.user.is_barangay_admin):
            return view_func(request, *args, **kwargs)
        messages.error(request, "Only barangay staff or admins can access that page.")
        return redirect("dashboard:home")

    return wrapper


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_barangay_admin:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Only admins can access that page.")
        return redirect("dashboard:home")

    return wrapper


def get_staff_assignment_options(complaint):
    staff_members = (
        User.objects.filter(role=User.Role.STAFF, is_active=True)
        .select_related("staff_profile")
        .prefetch_related("staff_profile__specialization_categories")
        .annotate(
            active_workload=Count(
                "assigned_complaints",
                filter=Q(assigned_complaints__status__in=ACTIVE_ASSIGNMENT_STATUSES),
            ),
            overdue_workload=Count(
                "assigned_complaints",
                filter=Q(
                    assigned_complaints__status__in=ACTIVE_ASSIGNMENT_STATUSES,
                    assigned_complaints__deadline_at__lt=timezone.now(),
                ),
            ),
        )
    )
    options = []
    for staff in staff_members:
        try:
            profile = staff.staff_profile
            availability = profile.availability
            availability_label = profile.get_availability_display()
            specializations = list(profile.specialization_categories.all())
            specialization_match = bool(complaint.category and complaint.category in specializations)
            team = profile.department or profile.position or "No team set"
        except Exception:
            availability = ""
            availability_label = "No availability set"
            specialization_match = False
            team = "No team set"

        availability_rank = {
            "AVAILABLE": 0,
            "BUSY": 1,
            "UNAVAILABLE": 2,
        }.get(availability, 3)
        score = availability_rank * 100 + staff.active_workload * 10 + staff.overdue_workload
        if specialization_match:
            score -= 20

        options.append(
            {
                "user": staff,
                "team": team,
                "availability": availability_label,
                "active_workload": staff.active_workload,
                "overdue_workload": staff.overdue_workload,
                "specialization_match": specialization_match,
                "score": score,
            }
        )
    return sorted(options, key=lambda item: (item["score"], item["user"].last_name, item["user"].first_name))[:8]


@login_required
def complaint_list_view(request):
    if request.user.is_barangay_admin:
        complaints = Complaint.objects.select_related("resident", "assigned_to", "category")
    elif request.user.is_staff_member:
        complaints = Complaint.objects.filter(
            Q(assigned_to=request.user) | Q(assigned_to__isnull=True)
        ).select_related("resident", "assigned_to", "category")
    else:
        complaints = Complaint.objects.filter(resident=request.user).select_related("resident", "assigned_to", "category")

    all_complaints = complaints
    status = request.GET.get("status")
    priority = request.GET.get("priority")
    search = request.GET.get("q", "").strip()
    if status:
        complaints = complaints.filter(status=status)
    if priority:
        complaints = complaints.filter(priority=priority)
    if search:
        search_filter = (
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(category__name__icontains=search)
            | Q(resident__first_name__icontains=search)
            | Q(resident__last_name__icontains=search)
            | Q(resident__username__icontains=search)
            | Q(assigned_to__first_name__icontains=search)
            | Q(assigned_to__last_name__icontains=search)
            | Q(assigned_to__username__icontains=search)
        )
        if search.isdigit():
            search_filter |= Q(id=int(search))
        complaints = complaints.filter(search_filter)
    status_counts = {
        item["status"]: item["total"]
        for item in all_complaints.values("status").annotate(total=Count("id"))
    }
    selected_status_label = dict(Complaint.Status.choices).get(status, "All statuses")
    selected_priority_label = dict(Complaint.Priority.choices).get(priority, "All priorities")

    return render(
        request,
        "complaints/complaint_list.html",
        {
            "complaints": complaints,
            "status_choices": Complaint.Status.choices,
            "priority_choices": Complaint.Priority.choices,
            "selected_status": status,
            "selected_status_label": selected_status_label,
            "selected_priority": priority,
            "selected_priority_label": selected_priority_label,
            "search_query": search,
            "total_count": all_complaints.count(),
            "pending_count": status_counts.get(Complaint.Status.PENDING, 0),
            "in_progress_count": status_counts.get(Complaint.Status.IN_PROGRESS, 0),
            "resolved_count": status_counts.get(Complaint.Status.RESOLVED, 0),
            "filtered_count": complaints.count(),
        },
    )


@login_required
def submit_complaint_view(request):
    if not request.user.is_resident:
        messages.error(request, "Only residents can submit complaints.")
        return redirect("dashboard:home")

    initial = {}
    if hasattr(request.user, "resident_profile") and request.user.resident_profile.phone_number:
        initial["contact_number"] = request.user.resident_profile.phone_number
    form = ComplaintForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        complaint = form.save(commit=False)
        complaint.resident = request.user
        complaint.save()
        ComplaintStatusHistory.objects.create(
            complaint=complaint,
            new_status=complaint.status,
            changed_by=request.user,
            remarks="Complaint submitted.",
        )
        if form.cleaned_data.get("evidence"):
            UploadedEvidence.objects.create(complaint=complaint, file=form.cleaned_data["evidence"])
        Notification.objects.create(
            user=request.user,
            complaint=complaint,
            message=f"Your complaint '{complaint.title}' was submitted successfully.",
        )
        messages.success(request, "Complaint submitted successfully.")
        return redirect(complaint.get_absolute_url())

    return render(request, "complaints/submit_complaint.html", {"form": form})


@login_required
def complaint_detail_view(request, pk):
    complaint = get_object_or_404(Complaint.objects.select_related("resident", "assigned_to", "category"), pk=pk)
    can_view = (
        request.user.is_barangay_admin
        or complaint.resident == request.user
        or (
            request.user.is_staff_member
            and (complaint.assigned_to == request.user or complaint.assigned_to is None)
        )
    )
    if not can_view:
        messages.error(request, "You do not have permission to view this complaint.")
        return redirect("complaints:list")
    if request.user.is_resident and complaint.resident == request.user:
        Notification.objects.filter(user=request.user, complaint=complaint, is_read=False).update(is_read=True)
    return render(request, "complaints/complaint_detail.html", {"complaint": complaint})


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).select_related("complaint")
    unread_count = notifications.filter(is_read=False).count()
    return render(
        request,
        "complaints/notifications.html",
        {"notifications": notifications, "unread_count": unread_count},
    )


@login_required
def mark_all_notifications_read_view(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect("complaints:notifications")


@login_required
@staff_or_admin_required
def update_complaint_view(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if request.user.is_staff_member and complaint.assigned_to not in (request.user, None):
        messages.error(request, "You can only update complaints assigned to you.")
        return redirect("complaints:list")

    form = ComplaintUpdateForm(request.POST or None, instance=complaint, complaint=complaint)
    if request.user.is_staff_member:
        form.fields.pop("assigned_to")

    if request.method == "POST" and form.is_valid():
        old_status = complaint.status
        old_priority = complaint.priority
        old_assigned_to = complaint.assigned_to
        complaint = form.save(commit=False)
        if request.user.is_staff_member and complaint.assigned_to is None:
            complaint.assigned_to = request.user
        if old_priority != complaint.priority and not complaint.is_closed:
            complaint.set_deadline(reference_time=timezone.now())
        if complaint.status == Complaint.Status.RESOLVED and old_status != Complaint.Status.RESOLVED:
            complaint.resolved_at = timezone.now()
        elif old_status == Complaint.Status.RESOLVED and complaint.status != Complaint.Status.RESOLVED:
            complaint.resolved_at = None
        complaint.save()
        remarks = form.cleaned_data.get("remarks")
        if remarks:
            ComplaintResponse.objects.create(
                complaint=complaint,
                responder=request.user,
                remarks=remarks,
                status_after_response=complaint.status,
            )
        if old_status != complaint.status:
            ComplaintStatusHistory.objects.create(
                complaint=complaint,
                old_status=old_status,
                new_status=complaint.status,
                changed_by=request.user,
                remarks=remarks or "",
            )
            Notification.objects.create(
                user=complaint.resident,
                complaint=complaint,
                message=f"Your complaint '{complaint.title}' is now {complaint.get_status_display()}.",
            )
        elif remarks:
            Notification.objects.create(
                user=complaint.resident,
                complaint=complaint,
                message=f"New remarks were added to your complaint '{complaint.title}'.",
            )
        if complaint.assigned_to and complaint.assigned_to != old_assigned_to:
            Notification.objects.create(
                user=complaint.assigned_to,
                complaint=complaint,
                message=f"You were assigned complaint '{complaint.title}'.",
            )
        messages.success(request, "Complaint updated successfully.")
        return redirect(complaint.get_absolute_url())

    return render(
        request,
        "complaints/update_complaint.html",
        {
            "form": form,
            "complaint": complaint,
            "staff_assignment_options": get_staff_assignment_options(complaint) if request.user.is_barangay_admin else [],
        },
    )


@login_required
@admin_required
def delete_complaint_view(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if request.method == "POST":
        complaint.delete()
        messages.success(request, "Complaint deleted successfully.")
        return redirect("complaints:list")
    return render(request, "complaints/delete_complaint.html", {"complaint": complaint})


@login_required
@admin_required
def reports_view(request):
    by_status = Complaint.objects.values("status").annotate(total=Count("id")).order_by("status")
    by_category = Complaint.objects.values("category__name").annotate(total=Count("id")).order_by("category__name")
    staff_workload = (
        User.objects.filter(role=User.Role.STAFF)
        .annotate(total_assigned=Count("assigned_complaints"))
        .order_by("last_name", "first_name")
    )
    return render(
        request,
        "complaints/reports.html",
        {"by_status": by_status, "by_category": by_category, "staff_workload": staff_workload},
    )
