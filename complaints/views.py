import csv
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.models import User
from .forms import (
    ComplaintForm,
    ComplaintCategoryForm,
    ComplaintReplyForm,
    ComplaintUpdateForm,
    EscalationForm,
    HearingAttendanceForm,
    HearingMediationForm,
    RespondentContactForm,
    RespondentForm,
    RespondentResponseForm,
    SecondNoticeForm,
)
from .models import (
    Complaint,
    ComplaintCategory,
    ComplaintReply,
    ComplaintResponse,
    ComplaintStatusHistory,
    Escalation,
    HearingMediation,
    Notification,
    Respondent,
    RespondentEvidence,
    UploadedEvidence,
)
from .services import choose_auto_assignee, create_notification, get_staff_assignment_options


ACTIVE_ASSIGNMENT_STATUSES = [
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


STATUS_NOTIFICATION_MESSAGES = {
    Complaint.Status.UNDER_REVIEW: "Your complaint is now under review by the barangay office.",
    Complaint.Status.RESPONDENT_CONTACTED: "The other party involved in your complaint has been contacted by the barangay office.",
    Complaint.Status.SECOND_NOTICE_SENT: "A second notice has been recorded for the other party involved in your complaint.",
    Complaint.Status.RESOLVED: "Your complaint has been marked as resolved.",
    Complaint.Status.UNRESOLVED: "Your complaint has been marked as unresolved.",
    Complaint.Status.ESCALATED: "Your complaint remains unresolved and has been escalated to a higher authority for further action.",
    Complaint.Status.CLOSED: "Your complaint has been closed.",
}


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


def record_status_change(complaint, old_status, new_status, user, public_remarks="", internal_remarks="", remarks=""):
    if old_status == new_status and not (public_remarks or internal_remarks or remarks):
        return
    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        old_status=old_status if old_status != new_status else "",
        new_status=new_status,
        changed_by=user,
        remarks=remarks,
        public_remarks=public_remarks,
        internal_remarks=internal_remarks,
    )


def notify_complainant_for_status(complaint, status, fallback_message=None):
    message = STATUS_NOTIFICATION_MESSAGES.get(status) or fallback_message
    if not message:
        message = f"Your complaint '{complaint.title}' is now {complaint.get_status_display()}."
    create_notification(
        user=complaint.resident,
        complaint=complaint,
        message=message,
        notification_type=Notification.Type.STATUS_CHANGED,
    )


def get_or_create_respondent(complaint):
    respondent, _ = Respondent.objects.get_or_create(
        complaint=complaint,
        defaults={"full_name": "Unknown"},
    )
    return respondent


def create_uploaded_evidence(complaint, file, user, evidence_type=UploadedEvidence.EvidenceType.INITIAL, description=""):
    return UploadedEvidence.objects.create(
        complaint=complaint,
        file=file,
        uploaded_by=user,
        evidence_type=evidence_type,
        description=description,
        file_size=getattr(file, "size", 0) or 0,
        content_type=getattr(file, "content_type", "") or "",
    )


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
        complaint.consented_at = timezone.now()
        complaint.save()
        Respondent.objects.create(
            complaint=complaint,
            full_name=form.cleaned_data.get("respondent_full_name") or "Unknown",
            contact_number=form.cleaned_data.get("respondent_contact_number", ""),
            address=form.cleaned_data.get("respondent_address", ""),
            relationship_to_complainant=form.cleaned_data.get("respondent_relationship_to_complainant", ""),
            is_known_to_complainant=form.cleaned_data.get("respondent_is_known_to_complainant", True),
            identifying_details=form.cleaned_data.get("respondent_identifying_details", ""),
            remarks=form.cleaned_data.get("respondent_remarks", ""),
        )
        auto_assignee = choose_auto_assignee(complaint)
        if auto_assignee:
            complaint.assigned_to = auto_assignee
            complaint.save(update_fields=["assigned_to"])
        ComplaintStatusHistory.objects.create(
            complaint=complaint,
            new_status=complaint.status,
            changed_by=request.user,
            remarks="Complaint submitted.",
            public_remarks="Your complaint has been submitted successfully.",
        )
        for evidence_file in form.cleaned_data.get("evidence", []):
            create_uploaded_evidence(complaint, evidence_file, request.user)
        create_notification(
            user=request.user,
            complaint=complaint,
            message=f"Your complaint '{complaint.title}' was submitted successfully.",
            notification_type=Notification.Type.SUBMITTED,
        )
        if auto_assignee:
            create_notification(
                user=auto_assignee,
                complaint=complaint,
                message=f"You were automatically assigned complaint '{complaint.title}'.",
                notification_type=Notification.Type.ASSIGNED,
            )
            create_notification(
                user=request.user,
                complaint=complaint,
                message=(
                    f"Your complaint '{complaint.title}' was assigned to "
                    f"{auto_assignee.get_full_name() or auto_assignee.username}."
                ),
                notification_type=Notification.Type.ASSIGNED,
            )
        messages.success(request, "Complaint submitted successfully.")
        return redirect(complaint.get_absolute_url())

    return render(request, "complaints/submit_complaint.html", {"form": form})


@login_required
def complaint_detail_view(request, pk):
    complaint = get_object_or_404(
        Complaint.objects.select_related("resident", "assigned_to", "category").prefetch_related(
            "status_history",
            "hearings",
            "evidence_files",
            "respondent_evidence_files",
            "responses",
            "replies",
        ),
        pk=pk,
    )
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

    reply_form = ComplaintReplyForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and request.POST.get("workflow_action") == "reply":
        if complaint.is_closed:
            messages.error(request, "This complaint is closed and cannot receive new replies.")
            return redirect(complaint.get_absolute_url())
        if reply_form.is_valid():
            reply = reply_form.save(commit=False)
            reply.complaint = complaint
            reply.author = request.user
            if request.user.is_staff_member or request.user.is_barangay_admin:
                reply.is_public = True
            if reply.attachment:
                reply.attachment_size = reply.attachment.size
                reply.attachment_content_type = getattr(reply.attachment, "content_type", "") or ""
            reply.save()
            if request.user == complaint.resident:
                recipient_ids = list(
                    User.objects.filter(Q(role=User.Role.ADMIN) | Q(is_superuser=True))
                    .values_list("id", flat=True)
                    .distinct()
                )
                if complaint.assigned_to:
                    recipient_ids.append(complaint.assigned_to_id)
                for recipient in User.objects.filter(id__in=set(recipient_ids)):
                    create_notification(
                        user=recipient,
                        complaint=complaint,
                        message=f"Resident added a follow-up to complaint '{complaint.title}'.",
                        notification_type=Notification.Type.REMARKS_ADDED,
                    )
            else:
                create_notification(
                    user=complaint.resident,
                    complaint=complaint,
                    message=f"Barangay staff replied to your complaint '{complaint.title}'.",
                    notification_type=Notification.Type.REMARKS_ADDED,
                )
            messages.success(request, "Reply added successfully.")
            return redirect(complaint.get_absolute_url())

    latest_hearing = complaint.hearings.first()
    public_status_history = complaint.status_history.exclude(public_remarks="")
    public_responses = complaint.responses.filter(is_public=True)
    return render(
        request,
        "complaints/complaint_detail.html",
        {
            "complaint": complaint,
            "latest_hearing": latest_hearing,
            "public_status_history": public_status_history,
            "public_responses": public_responses,
            "reply_form": reply_form,
        },
    )


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
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True, read_at=timezone.now())
        messages.success(request, "All notifications marked as read.")
    return redirect("complaints:notifications")


@login_required
def notification_view_redirect(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])

    if notification.link_target:
        return redirect(notification.link_target)
    if notification.complaint:
        return redirect(notification.complaint.get_absolute_url())
    return redirect("complaints:notifications")


def get_workflow_guidance(complaint, action=None):
    action_tabs = {
        "complaint": "assignment",
        "respondent": "respondent",
        "contact": "contact",
        "response": "contact",
        "hearing": "hearing",
        "attendance": "hearing",
        "second_notice": "resolution",
        "escalation": "resolution",
    }
    status_guidance = {
        Complaint.Status.PENDING: (
            "assignment",
            "Assign and triage this complaint",
            "Set the priority, choose a handler, and add any initial public or internal remarks.",
            "bi-person-check-fill",
        ),
        Complaint.Status.UNDER_REVIEW: (
            "respondent",
            "Complete respondent details",
            "Review the other party information before contact or mediation work starts.",
            "bi-person-lines-fill",
        ),
        Complaint.Status.RESPONDENT_NOT_CONTACTED: (
            "contact",
            "Record the first contact attempt",
            "Capture how the respondent was contacted and whether they already gave a response.",
            "bi-telephone-fill",
        ),
        Complaint.Status.RESPONDENT_CONTACTED: (
            "contact",
            "Record the respondent response",
            "Add the response statement or supporting attachment once the other party replies.",
            "bi-chat-left-text-fill",
        ),
        Complaint.Status.WAITING_RESPONDENT_RESPONSE: (
            "contact",
            "Follow up on the respondent response",
            "Update the response status, or record no response if the deadline has passed.",
            "bi-hourglass-split",
        ),
        Complaint.Status.RESPONDENT_RESPONSE_RECORDED: (
            "hearing",
            "Schedule hearing or mediation",
            "Move the complaint into a scheduled hearing or mediation session if needed.",
            "bi-calendar-event-fill",
        ),
        Complaint.Status.NO_RESPONSE: (
            "resolution",
            "Record a second notice",
            "Use the second notice section when the respondent did not answer the first contact.",
            "bi-envelope-paper-fill",
        ),
        Complaint.Status.FAILED_TO_ATTEND: (
            "resolution",
            "Record second notice or escalate",
            "Use the resolution tools when attendance failed or further action is required.",
            "bi-exclamation-triangle-fill",
        ),
        Complaint.Status.SECOND_NOTICE_SENT: (
            "hearing",
            "Schedule the next hearing step",
            "After the second notice, schedule or update hearing and mediation details.",
            "bi-calendar-plus-fill",
        ),
        Complaint.Status.HEARING_SCHEDULED: (
            "hearing",
            "Record attendance and result",
            "After the scheduled date, record attendance and the mediation outcome.",
            "bi-clipboard2-check-fill",
        ),
        Complaint.Status.IN_MEDIATION: (
            "hearing",
            "Update mediation result",
            "Record whether the mediation resolved the issue, needs rescheduling, or must be escalated.",
            "bi-people-fill",
        ),
        Complaint.Status.IN_PROGRESS: (
            "resolution",
            "Add resolution updates",
            "Use status remarks, escalation, or final resolution updates as the case progresses.",
            "bi-arrow-repeat",
        ),
        Complaint.Status.UNRESOLVED: (
            "resolution",
            "Escalate or close the unresolved case",
            "Escalate when barangay-level handling cannot resolve the complaint.",
            "bi-arrow-up-right-circle-fill",
        ),
        Complaint.Status.ESCALATED: (
            "resolution",
            "Track escalation outcome",
            "Keep internal notes and update the status when a higher authority responds.",
            "bi-arrow-up-right-circle-fill",
        ),
        Complaint.Status.RESOLVED: (
            "resolution",
            "Review the resolved complaint",
            "The complaint is resolved. Add only necessary final notes or corrections.",
            "bi-check-circle-fill",
        ),
        Complaint.Status.CLOSED: (
            "resolution",
            "Complaint is closed",
            "This complaint is closed. Review details before making any further change.",
            "bi-lock-fill",
        ),
        Complaint.Status.REJECTED: (
            "resolution",
            "Review rejected complaint",
            "Check remarks and supporting details before reopening or changing the outcome.",
            "bi-x-circle-fill",
        ),
    }
    active_tab, title, body, icon = status_guidance.get(
        complaint.status,
        (
            "assignment",
            "Review complaint workflow",
            "Choose the section that matches the work you need to record.",
            "bi-kanban-fill",
        ),
    )
    return {
        "workflow_active_tab": action_tabs.get(action, active_tab),
        "workflow_recommendation_title": title,
        "workflow_recommendation_body": body,
        "workflow_recommendation_icon": icon,
    }


@login_required
@staff_or_admin_required
def update_complaint_view(request, pk):
    complaint = get_object_or_404(Complaint.objects.select_related("resident", "assigned_to", "category"), pk=pk)
    if request.user.is_staff_member and complaint.assigned_to not in (request.user, None):
        messages.error(request, "You can only update complaints assigned to you.")
        return redirect("complaints:list")

    respondent = get_or_create_respondent(complaint)
    latest_hearing = complaint.hearings.first()
    escalation = getattr(complaint, "escalation", None)
    action = request.POST.get("workflow_action") if request.method == "POST" else None
    form = ComplaintUpdateForm(
        request.POST if action == "complaint" else None,
        instance=complaint,
        complaint=complaint,
        prefix="complaint",
    )
    respondent_form = RespondentForm(
        request.POST if action == "respondent" else None,
        instance=respondent,
        prefix="respondent",
    )
    contact_form = RespondentContactForm(
        request.POST if action == "contact" else None,
        instance=respondent,
        prefix="contact",
    )
    response_form = RespondentResponseForm(
        request.POST if action == "response" else None,
        request.FILES if action == "response" else None,
        prefix="response",
    )
    hearing_form = HearingMediationForm(request.POST if action == "hearing" else None, prefix="hearing")
    attendance_form = (
        HearingAttendanceForm(
            request.POST if action == "attendance" else None,
            instance=latest_hearing,
            prefix="attendance",
        )
        if latest_hearing
        else None
    )
    second_notice_form = SecondNoticeForm(
        request.POST if action == "second_notice" else None,
        instance=complaint,
        prefix="second_notice",
    )
    escalation_form = EscalationForm(
        request.POST if action == "escalation" else None,
        instance=escalation,
        prefix="escalation",
    )
    if request.user.is_staff_member:
        form.fields.pop("assigned_to")
    workflow_context = get_workflow_guidance(complaint, action)

    if request.method == "POST" and action == "complaint":
        old_status = complaint.status
        old_priority = complaint.priority
        old_assigned_to = complaint.assigned_to
        if not form.is_valid():
            return render(
                request,
                "complaints/update_complaint.html",
                {
                    "form": form,
                    "complaint": complaint,
                    "respondent": respondent,
                    "respondent_form": respondent_form,
                    "contact_form": contact_form,
                    "response_form": response_form,
                    "hearing_form": hearing_form,
                    "attendance_form": attendance_form,
                    "second_notice_form": second_notice_form,
                    "escalation_form": escalation_form,
                    "latest_hearing": latest_hearing,
                    "staff_assignment_options": get_staff_assignment_options(complaint) if request.user.is_barangay_admin else [],
                    **workflow_context,
                },
            )
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
        public_remarks = form.cleaned_data.get("public_remarks_input", "").strip()
        internal_remarks = form.cleaned_data.get("internal_remarks_input", "").strip()
        if public_remarks:
            complaint.public_remarks = public_remarks
        if internal_remarks:
            complaint.internal_remarks = internal_remarks
        if public_remarks or internal_remarks:
            complaint.save(update_fields=["public_remarks", "internal_remarks", "updated_at"])
        if public_remarks:
            ComplaintResponse.objects.create(
                complaint=complaint,
                responder=request.user,
                remarks=public_remarks,
                is_public=True,
                status_after_response=complaint.status,
            )
        if internal_remarks:
            ComplaintResponse.objects.create(
                complaint=complaint,
                responder=request.user,
                remarks=internal_remarks,
                is_public=False,
                status_after_response=complaint.status,
            )
        if old_status != complaint.status:
            record_status_change(
                complaint,
                old_status,
                complaint.status,
                request.user,
                public_remarks=public_remarks or complaint.public_remarks,
                internal_remarks=internal_remarks,
            )
            notify_complainant_for_status(complaint, complaint.status)
        elif public_remarks or internal_remarks:
            record_status_change(
                complaint,
                complaint.status,
                complaint.status,
                request.user,
                public_remarks=public_remarks,
                internal_remarks=internal_remarks,
            )
        if public_remarks:
            create_notification(
                user=complaint.resident,
                complaint=complaint,
                message=f"New remarks were added to your complaint '{complaint.title}'.",
                notification_type=Notification.Type.REMARKS_ADDED,
            )
        if complaint.assigned_to and complaint.assigned_to != old_assigned_to:
            create_notification(
                user=complaint.assigned_to,
                complaint=complaint,
                message=f"You were assigned complaint '{complaint.title}'.",
                notification_type=Notification.Type.ASSIGNED,
            )
            create_notification(
                user=complaint.resident,
                complaint=complaint,
                message=(
                    f"Your complaint '{complaint.title}' was assigned to "
                    f"{complaint.assigned_to.get_full_name() or complaint.assigned_to.username}."
                ),
                notification_type=Notification.Type.ASSIGNED,
            )
        messages.success(request, "Complaint updated successfully.")
        return redirect(complaint.get_absolute_url())

    if request.method == "POST" and action == "respondent" and respondent_form.is_valid():
        respondent_form.save()
        messages.success(request, "Respondent details updated.")
        return redirect(complaint.get_absolute_url())

    if request.method == "POST" and action == "contact" and contact_form.is_valid():
        old_status = complaint.status
        respondent = contact_form.save(commit=False)
        if respondent.contacted:
            respondent.contacted_by = request.user
            if not respondent.contact_date:
                respondent.contact_date = timezone.localdate()
            complaint.status = Complaint.Status.RESPONDENT_CONTACTED
        elif complaint.status == Complaint.Status.PENDING:
            complaint.status = Complaint.Status.RESPONDENT_NOT_CONTACTED
        if respondent.response_status == Respondent.ResponseStatus.RESPONDED:
            complaint.status = Complaint.Status.RESPONDENT_RESPONSE_RECORDED
        elif respondent.response_status == Respondent.ResponseStatus.NO_RESPONSE:
            complaint.status = Complaint.Status.NO_RESPONSE
        elif respondent.response_status == Respondent.ResponseStatus.FAILED_TO_ATTEND:
            complaint.status = Complaint.Status.FAILED_TO_ATTEND
        respondent.save()
        complaint.save(update_fields=["status", "updated_at"])
        public_remarks = ""
        if complaint.status == Complaint.Status.RESPONDENT_CONTACTED:
            public_remarks = "The other party involved in your complaint has been contacted by the barangay office."
        record_status_change(
            complaint,
            old_status,
            complaint.status,
            request.user,
            public_remarks=public_remarks,
            internal_remarks=respondent.contact_remarks,
        )
        notify_complainant_for_status(complaint, complaint.status)
        messages.success(request, "Respondent contact details recorded.")
        return redirect(complaint.get_absolute_url())

    if request.method == "POST" and action == "response" and response_form.is_valid():
        old_status = complaint.status
        response = response_form.save(commit=False)
        response.complaint = complaint
        response.responder = request.user
        response.source = ComplaintResponse.Source.RESPONDENT
        response.is_public = False
        response.status_after_response = Complaint.Status.RESPONDENT_RESPONSE_RECORDED
        response.save()
        respondent.response_status = Respondent.ResponseStatus.RESPONDED
        respondent.response_statement = response.remarks
        respondent.save(update_fields=["response_status", "response_statement", "updated_at"])
        if response_form.cleaned_data.get("evidence"):
            RespondentEvidence.objects.create(
                complaint=complaint,
                file=response_form.cleaned_data["evidence"],
                uploaded_by=request.user,
                evidence_type=RespondentEvidence.EvidenceType.RESPONSE,
                remarks=response_form.cleaned_data.get("evidence_remarks", ""),
                file_size=getattr(response_form.cleaned_data["evidence"], "size", 0) or 0,
                content_type=getattr(response_form.cleaned_data["evidence"], "content_type", "") or "",
            )
        complaint.status = Complaint.Status.RESPONDENT_RESPONSE_RECORDED
        complaint.save(update_fields=["status", "updated_at"])
        record_status_change(
            complaint,
            old_status,
            complaint.status,
            request.user,
            public_remarks="The barangay office has recorded the other party's response.",
            internal_remarks=response.remarks,
        )
        notify_complainant_for_status(complaint, complaint.status)
        messages.success(request, "Respondent response recorded.")
        return redirect(complaint.get_absolute_url())

    if request.method == "POST" and action == "hearing" and hearing_form.is_valid():
        old_status = complaint.status
        hearing = hearing_form.save(commit=False)
        hearing.complaint = complaint
        hearing.created_by = request.user
        hearing.save()
        complaint.status = Complaint.Status.HEARING_SCHEDULED
        complaint.save(update_fields=["status", "updated_at"])
        public_remarks = (
            f"Your complaint hearing has been scheduled on {hearing.date} "
            f"at {hearing.time.strftime('%I:%M %p')} in {hearing.location}. Please attend on time."
        )
        record_status_change(complaint, old_status, complaint.status, request.user, public_remarks=public_remarks)
        create_notification(
            user=complaint.resident,
            complaint=complaint,
            message=public_remarks,
            notification_type=Notification.Type.STATUS_CHANGED,
        )
        messages.success(request, "Hearing or mediation schedule saved.")
        return redirect(complaint.get_absolute_url())

    if request.method == "POST" and action == "attendance" and attendance_form and attendance_form.is_valid():
        old_status = complaint.status
        hearing = attendance_form.save(commit=False)
        hearing.attendance_recorded = True
        hearing.save()
        if hearing.mediation_result == HearingMediation.MediationResult.RESOLVED:
            complaint.status = Complaint.Status.RESOLVED
            complaint.resolved_at = timezone.now()
        elif hearing.mediation_result == HearingMediation.MediationResult.UNRESOLVED:
            complaint.status = Complaint.Status.UNRESOLVED
        elif hearing.mediation_result == HearingMediation.MediationResult.FOR_ESCALATION:
            complaint.status = Complaint.Status.UNRESOLVED
        elif hearing.mediation_result == HearingMediation.MediationResult.RESCHEDULED:
            complaint.status = Complaint.Status.HEARING_SCHEDULED
        else:
            complaint.status = Complaint.Status.IN_MEDIATION
        complaint.save(update_fields=["status", "resolved_at", "updated_at"])
        public_remarks = hearing.agreement_remarks if hearing.mediation_result == HearingMediation.MediationResult.RESOLVED else ""
        record_status_change(
            complaint,
            old_status,
            complaint.status,
            request.user,
            public_remarks=public_remarks,
            internal_remarks=hearing.attendance_remarks,
        )
        notify_complainant_for_status(complaint, complaint.status)
        messages.success(request, "Attendance and mediation result recorded.")
        return redirect(complaint.get_absolute_url())

    if request.method == "POST" and action == "second_notice" and second_notice_form.is_valid():
        old_status = complaint.status
        complaint = second_notice_form.save(commit=False)
        complaint.second_notice_sent = True
        if not complaint.second_notice_date:
            complaint.second_notice_date = timezone.localdate()
        complaint.status = Complaint.Status.SECOND_NOTICE_SENT
        complaint.save()
        record_status_change(
            complaint,
            old_status,
            complaint.status,
            request.user,
            public_remarks="A second notice has been recorded for the other party involved in your complaint.",
            internal_remarks=complaint.second_notice_remarks,
        )
        notify_complainant_for_status(complaint, complaint.status)
        messages.success(request, "Second notice recorded.")
        return redirect(complaint.get_absolute_url())

    if request.method == "POST" and action == "escalation" and escalation_form.is_valid():
        old_status = complaint.status
        escalation = escalation_form.save(commit=False)
        escalation.complaint = complaint
        escalation.escalated = True
        escalation.escalated_by = request.user
        escalation.save()
        complaint.status = Complaint.Status.ESCALATED
        complaint.save(update_fields=["status", "updated_at"])
        record_status_change(
            complaint,
            old_status,
            complaint.status,
            request.user,
            public_remarks="The complaint has been escalated for further action.",
            internal_remarks=escalation.remarks,
        )
        notify_complainant_for_status(complaint, complaint.status)
        messages.success(request, "Complaint escalated.")
        return redirect(complaint.get_absolute_url())

    return render(
        request,
        "complaints/update_complaint.html",
        {
            "form": form,
            "complaint": complaint,
            "respondent": respondent,
            "respondent_form": respondent_form,
            "contact_form": contact_form,
            "response_form": response_form,
            "hearing_form": hearing_form,
            "attendance_form": attendance_form,
            "second_notice_form": second_notice_form,
            "escalation_form": escalation_form,
            "latest_hearing": latest_hearing,
            "staff_assignment_options": get_staff_assignment_options(complaint) if request.user.is_barangay_admin else [],
            **workflow_context,
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


def get_report_complaints(request):
    date_from = parse_date(request.GET.get("date_from") or "")
    date_to = parse_date(request.GET.get("date_to") or "")
    complaints = Complaint.objects.select_related("category", "resident", "assigned_to")
    if date_from:
        complaints = complaints.filter(created_at__date__gte=date_from)
    if date_to:
        complaints = complaints.filter(created_at__date__lte=date_to)
    return complaints, date_from, date_to


@login_required
@admin_required
def reports_view(request):
    complaints, date_from, date_to = get_report_complaints(request)

    status_labels = dict(Complaint.Status.choices)
    by_status = [
        {**row, "label": status_labels.get(row["status"], row["status"])}
        for row in complaints.values("status").annotate(total=Count("id")).order_by("status")
    ]
    by_category = complaints.values("category__name").annotate(total=Count("id")).order_by("category__name")
    staff_workload = (
        User.objects.filter(role=User.Role.STAFF)
        .annotate(total_assigned=Count("assigned_complaints", filter=Q(assigned_complaints__in=complaints)))
        .order_by("last_name", "first_name")
    )
    total_complaints = complaints.count()
    resolved_count = complaints.filter(status=Complaint.Status.RESOLVED).count()
    pending_count = complaints.filter(status=Complaint.Status.PENDING).count()
    overdue_count = sum(1 for complaint in complaints if complaint.is_overdue)
    resolved_with_duration = complaints.filter(resolved_at__isnull=False).annotate(
        resolution_duration=ExpressionWrapper(F("resolved_at") - F("created_at"), output_field=DurationField())
    )
    average_resolution = resolved_with_duration.aggregate(value=Avg("resolution_duration"))["value"]
    average_resolution_hours = round(average_resolution.total_seconds() / 3600, 1) if average_resolution else 0
    by_location = complaints.values("incident_location").annotate(total=Count("id")).order_by("-total")[:10]
    return render(
        request,
        "complaints/reports.html",
        {
            "by_status": by_status,
            "by_category": by_category,
            "staff_workload": staff_workload,
            "total_complaints": total_complaints,
            "resolved_count": resolved_count,
            "pending_count": pending_count,
            "overdue_count": overdue_count,
            "average_resolution_hours": average_resolution_hours,
            "by_location": by_location,
            "date_from": request.GET.get("date_from", ""),
            "date_to": request.GET.get("date_to", ""),
        },
    )


@login_required
@admin_required
def reports_export_csv_view(request):
    complaints, _, _ = get_report_complaints(request)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="barangay-complaints-report.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "ID",
            "Title",
            "Category",
            "Priority",
            "Status",
            "Resident",
            "Assigned To",
            "Incident Location",
            "Created At",
            "Deadline",
            "Resolved At",
        ]
    )
    for complaint in complaints.order_by("-created_at"):
        writer.writerow(
            [
                complaint.id,
                complaint.title,
                complaint.category.name if complaint.category else "Uncategorized",
                complaint.get_priority_display(),
                complaint.get_status_display(),
                complaint.resident.get_full_name() or complaint.resident.username,
                complaint.assigned_to.get_full_name() or complaint.assigned_to.username if complaint.assigned_to else "",
                complaint.incident_location,
                complaint.created_at.strftime("%Y-%m-%d %H:%M"),
                complaint.deadline_at.strftime("%Y-%m-%d %H:%M") if complaint.deadline_at else "",
                complaint.resolved_at.strftime("%Y-%m-%d %H:%M") if complaint.resolved_at else "",
            ]
        )
    return response


@login_required
@admin_required
def reports_export_pdf_view(request):
    complaints, _, _ = get_report_complaints(request)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        messages.error(request, "PDF export needs reportlab. Install requirements.txt, then try again.")
        return redirect("complaints:reports")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Barangay Cawitan Complaints Report")
    y -= 30
    pdf.setFont("Helvetica", 9)
    for complaint in complaints.order_by("-created_at")[:80]:
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 9)
            y = height - 50
        line = (
            f"#{complaint.id} {complaint.title[:42]} | {complaint.get_status_display()} | "
            f"{complaint.get_priority_display()} | {complaint.created_at:%Y-%m-%d}"
        )
        pdf.drawString(50, y, line)
        y -= 16
    pdf.save()
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="barangay-complaints-report.pdf"'
    return response


@login_required
@admin_required
def category_management_view(request):
    categories = ComplaintCategory.objects.annotate(total_complaints=Count("complaint")).order_by("name")
    return render(request, "complaints/category_management.html", {"categories": categories})


@login_required
@admin_required
def category_create_view(request):
    form = ComplaintCategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category created successfully.")
        return redirect("complaints:categories")
    return render(request, "complaints/category_form.html", {"form": form, "category": None})


@login_required
@admin_required
def category_edit_view(request, pk):
    category = get_object_or_404(ComplaintCategory, pk=pk)
    form = ComplaintCategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category updated successfully.")
        return redirect("complaints:categories")
    return render(request, "complaints/category_form.html", {"form": form, "category": category})


@login_required
@admin_required
def category_toggle_view(request, pk):
    if request.method != "POST":
        return redirect("complaints:categories")
    category = get_object_or_404(ComplaintCategory, pk=pk)
    category.is_active = not category.is_active
    category.save(update_fields=["is_active"])
    messages.success(request, f"{category.name} has been {'activated' if category.is_active else 'deactivated'}.")
    return redirect("complaints:categories")
