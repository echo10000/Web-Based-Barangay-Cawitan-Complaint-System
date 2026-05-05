from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from .forms import ComplaintForm, ComplaintUpdateForm
from .models import Complaint, ComplaintResponse, Notification, UploadedEvidence


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


@login_required
def complaint_list_view(request):
    if request.user.is_barangay_admin:
        complaints = Complaint.objects.select_related("resident", "assigned_to", "category")
    elif request.user.is_staff_member:
        complaints = Complaint.objects.filter(assigned_to=request.user).select_related("resident", "assigned_to", "category")
    else:
        complaints = Complaint.objects.filter(resident=request.user).select_related("resident", "assigned_to", "category")

    status = request.GET.get("status")
    if status:
        complaints = complaints.filter(status=status)

    return render(
        request,
        "complaints/complaint_list.html",
        {"complaints": complaints, "status_choices": Complaint.Status.choices, "selected_status": status},
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
        or (request.user.is_staff_member and complaint.assigned_to == request.user)
    )
    if not can_view:
        messages.error(request, "You do not have permission to view this complaint.")
        return redirect("complaints:list")
    if request.user.is_resident and complaint.resident == request.user:
        Notification.objects.filter(user=request.user, complaint=complaint, is_read=False).update(is_read=True)
    return render(request, "complaints/complaint_detail.html", {"complaint": complaint})


@login_required
def notifications_view(request):
    if not request.user.is_resident:
        messages.error(request, "Notifications are available for residents only.")
        return redirect("dashboard:home")

    notifications = Notification.objects.filter(user=request.user).select_related("complaint")
    unread_count = notifications.filter(is_read=False).count()
    return render(
        request,
        "complaints/notifications.html",
        {"notifications": notifications, "unread_count": unread_count},
    )


@login_required
def mark_all_notifications_read_view(request):
    if not request.user.is_resident:
        messages.error(request, "Notifications are available for residents only.")
        return redirect("dashboard:home")

    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect("complaints:notifications")


@login_required
@staff_or_admin_required
def update_complaint_view(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if request.user.is_staff_member and complaint.assigned_to != request.user:
        messages.error(request, "You can only update complaints assigned to you.")
        return redirect("complaints:list")

    form = ComplaintUpdateForm(request.POST or None, instance=complaint)
    if request.user.is_staff_member:
        form.fields.pop("assigned_to")

    if request.method == "POST" and form.is_valid():
        old_status = complaint.status
        complaint = form.save()
        remarks = form.cleaned_data.get("remarks")
        if remarks:
            ComplaintResponse.objects.create(
                complaint=complaint,
                responder=request.user,
                remarks=remarks,
                status_after_response=complaint.status,
            )
        if old_status != complaint.status:
            Notification.objects.create(
                user=complaint.resident,
                complaint=complaint,
                message=f"Your complaint '{complaint.title}' is now {complaint.get_status_display()}.",
            )
        messages.success(request, "Complaint updated successfully.")
        return redirect(complaint.get_absolute_url())

    return render(request, "complaints/update_complaint.html", {"form": form, "complaint": complaint})


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
