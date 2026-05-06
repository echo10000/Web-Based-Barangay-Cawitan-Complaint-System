import csv
from datetime import datetime
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
    ComplaintFeeForm,
    ComplaintFeedbackForm,
    ComplaintForm,
    ComplaintCategoryForm,
    EvidenceReviewForm,
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
    ActivityLog,
    Complaint,
    ComplaintCategory,
    ComplaintFeedback,
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
from .services import choose_auto_assignee, create_notification, get_staff_assignment_options, log_activity


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


def generate_fee_receipt_number(complaint):
    year = timezone.localdate().year
    return f"FEE-{year}-CMP{complaint.pk:05d}"


def get_or_create_respondent(complaint):
    respondent, _ = Respondent.objects.get_or_create(
        complaint=complaint,
        defaults={"full_name": "Unknown"},
    )
    return respondent


def create_uploaded_evidence(complaint, file, user, evidence_type=UploadedEvidence.EvidenceType.INITIAL, description=""):
    evidence = UploadedEvidence.objects.create(
        complaint=complaint,
        file=file,
        uploaded_by=user,
        evidence_type=evidence_type,
        description=description,
        file_size=getattr(file, "size", 0) or 0,
        content_type=getattr(file, "content_type", "") or "",
    )
    log_activity(
        actor=user,
        complaint=complaint,
        action=ActivityLog.Action.EVIDENCE_UPLOADED,
        target=evidence,
        summary=f"Evidence uploaded for complaint '{complaint.title}'.",
    )
    return evidence


def build_complaint_timeline(complaint, *, staff_view=False):
    timeline = [
        {
            "when": complaint.created_at,
            "title": "Complaint submitted",
            "body": "The complaint record was created.",
            "kind": "submitted",
            "is_public": True,
        }
    ]
    for item in complaint.status_history.all():
        if not staff_view and not item.public_remarks:
            continue
        title = item.get_new_status_display()
        if staff_view and item.old_status:
            title = f"{item.get_old_status_display()} to {item.get_new_status_display()}"
        timeline.append(
            {
                "when": item.changed_at,
                "title": title,
                "body": item.public_remarks or item.remarks or item.internal_remarks,
                "actor": item.changed_by,
                "kind": "status",
                "is_public": bool(item.public_remarks),
            }
        )
    for hearing in complaint.hearings.all():
        timeline.append(
            {
                "when": timezone.make_aware(
                    datetime.combine(hearing.date, hearing.time),
                    timezone.get_current_timezone(),
                ),
                "title": "Hearing / mediation scheduled",
                "body": f"{hearing.purpose} at {hearing.location}. {hearing.remarks}".strip(),
                "actor": hearing.created_by,
                "kind": "hearing",
                "is_public": True,
            }
        )
    if staff_view:
        for reply in complaint.replies.all():
            timeline.append(
                {
                    "when": reply.created_at,
                    "title": "Follow-up reply",
                    "body": reply.message,
                    "actor": reply.author,
                    "kind": "reply",
                    "is_public": reply.is_public,
                }
            )
        for response in complaint.responses.all():
            timeline.append(
                {
                    "when": response.created_at,
                    "title": response.get_source_display(),
                    "body": response.remarks,
                    "actor": response.responder,
                    "kind": "response",
                    "is_public": response.is_public,
                }
            )
        for log in complaint.activity_logs.all():
            timeline.append(
                {
                    "when": log.created_at,
                    "title": log.get_action_display(),
                    "body": log.summary,
                    "actor": log.actor,
                    "kind": "activity",
                    "is_public": False,
                }
            )
    return sorted(timeline, key=lambda item: item["when"], reverse=True)


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
    try:
        resident_profile = request.user.resident_profile
    except Exception:
        resident_profile = None
    if not resident_profile or resident_profile.verification_status != resident_profile.VerificationStatus.VERIFIED:
        messages.error(request, "Your resident account must be verified before you can submit a complaint.")
        return redirect("accounts:profile")

    initial = {}
    if resident_profile.phone_number:
        initial["contact_number"] = resident_profile.phone_number
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
        log_activity(
            actor=request.user,
            complaint=complaint,
            action=ActivityLog.Action.COMPLAINT_SUBMITTED,
            target=complaint,
            summary=f"Complaint '{complaint.title}' submitted.",
        )
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
            "activity_logs",
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
    feedback_form = ComplaintFeedbackForm(request.POST or None)
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

    if request.method == "POST" and request.POST.get("workflow_action") == "feedback":
        if request.user != complaint.resident:
            messages.error(request, "Only the complainant can submit feedback.")
            return redirect(complaint.get_absolute_url())
        if complaint.status != Complaint.Status.RESOLVED:
            messages.error(request, "Feedback can only be submitted after the complaint is resolved.")
            return redirect(complaint.get_absolute_url())
        if hasattr(complaint, "feedback"):
            messages.error(request, "Feedback has already been submitted for this complaint.")
            return redirect(complaint.get_absolute_url())
        if feedback_form.is_valid():
            feedback = feedback_form.save(commit=False)
            feedback.complaint = complaint
            feedback.resident = request.user
            feedback.save()
            log_activity(
                actor=request.user,
                complaint=complaint,
                action=ActivityLog.Action.FEEDBACK_SUBMITTED,
                target=feedback,
                summary=f"Resident feedback submitted for complaint '{complaint.title}'.",
                metadata={"rating": feedback.rating, "resolution_accepted": feedback.resolution_accepted},
            )
            messages.success(request, "Thank you. Your feedback has been recorded.")
            return redirect(complaint.get_absolute_url())

    if request.method == "POST" and request.POST.get("workflow_action") == "evidence_review":
        if not (request.user.is_staff_member or request.user.is_barangay_admin):
            messages.error(request, "Only staff or admins can review evidence.")
            return redirect(complaint.get_absolute_url())
        evidence_kind = request.POST.get("evidence_kind")
        evidence_id = request.POST.get("evidence_id")
        evidence_model = RespondentEvidence if evidence_kind == "respondent" else UploadedEvidence
        evidence = get_object_or_404(evidence_model, pk=evidence_id, complaint=complaint)
        review_form = EvidenceReviewForm(request.POST)
        if review_form.is_valid():
            evidence.review_status = review_form.cleaned_data["review_status"]
            evidence.review_remarks = review_form.cleaned_data["review_remarks"]
            evidence.reviewed_by = request.user
            evidence.reviewed_at = timezone.now()
            evidence.save(update_fields=["review_status", "review_remarks", "reviewed_by", "reviewed_at"])
            log_activity(
                actor=request.user,
                complaint=complaint,
                action=ActivityLog.Action.EVIDENCE_REVIEWED,
                target=evidence,
                summary=f"Evidence marked {evidence.get_review_status_display()} for complaint '{complaint.title}'.",
            )
            messages.success(request, "Evidence review saved.")
            return redirect(complaint.get_absolute_url())

    latest_hearing = complaint.hearings.first()
    public_status_history = complaint.status_history.exclude(public_remarks="")
    public_responses = complaint.responses.filter(is_public=True)
    staff_view = request.user.is_staff_member or request.user.is_barangay_admin
    return render(
        request,
        "complaints/complaint_detail.html",
        {
            "complaint": complaint,
            "latest_hearing": latest_hearing,
            "public_status_history": public_status_history,
            "public_responses": public_responses,
            "reply_form": reply_form,
            "feedback_form": feedback_form,
            "complaint_timeline": build_complaint_timeline(complaint, staff_view=staff_view),
            "evidence_review_choices": UploadedEvidence.ReviewStatus.choices,
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


def build_notice_pdf_response(request, complaint, title, lines, filename):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        messages.error(request, "PDF generation needs reportlab. Install requirements.txt, then try again.")
        return None

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    _, height = letter
    y = height - 50
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Barangay Cawitan")
    y -= 22
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, title)
    y -= 30
    pdf.setFont("Helvetica", 10)
    for line in lines:
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = height - 50
        pdf.drawString(50, y, str(line)[:100])
        y -= 18
    pdf.save()
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@staff_or_admin_required
def complaint_notice_pdf_view(request, pk, notice_type):
    complaint = get_object_or_404(
        Complaint.objects.select_related("resident", "assigned_to", "category").prefetch_related("hearings"),
        pk=pk,
    )
    if request.user.is_staff_member and complaint.assigned_to not in (request.user, None):
        messages.error(request, "You can only generate notices for complaints assigned to you.")
        return redirect("complaints:list")

    latest_hearing = complaint.hearings.first()
    respondent = getattr(complaint, "respondent", None)
    base_lines = [
        f"Complaint No.: CMP-{complaint.id:03d}",
        f"Title: {complaint.title}",
        f"Complainant: {complaint.resident.get_full_name() or complaint.resident.username}",
        f"Respondent: {respondent.full_name if respondent else 'Unknown'}",
        f"Category: {complaint.category.name if complaint.category else 'Uncategorized'}",
        f"Status: {complaint.get_status_display()}",
        "",
    ]
    if notice_type == "hearing":
        if not latest_hearing:
            messages.error(request, "Schedule a hearing before generating a hearing notice.")
            return redirect(complaint.get_absolute_url())
        title = "Hearing / Mediation Notice"
        lines = base_lines + [
            f"Date: {latest_hearing.date:%B %d, %Y}",
            f"Time: {latest_hearing.time:%I:%M %p}",
            f"Location: {latest_hearing.location}",
            f"Purpose: {latest_hearing.purpose}",
            f"Instructions: {latest_hearing.remarks or 'Please attend on time.'}",
        ]
    elif notice_type == "second-notice":
        title = "Second Notice"
        lines = base_lines + [
            f"Notice Date: {complaint.second_notice_date or timezone.localdate()}",
            f"Method: {complaint.second_notice_method or 'Not recorded'}",
            f"Remarks: {complaint.second_notice_remarks or 'Second notice recorded by the barangay office.'}",
        ]
    else:
        title = "Complaint Resolution Summary"
        lines = base_lines + [
            f"Resolved At: {complaint.resolved_at:%B %d, %Y %I:%M %p}" if complaint.resolved_at else "Resolved At: Not recorded",
            f"Public Remarks: {complaint.public_remarks or 'No public remarks recorded.'}",
            f"Escalation: {complaint.escalation.escalated_to if hasattr(complaint, 'escalation') else 'Not escalated'}",
        ]
    log_activity(
        actor=request.user,
        complaint=complaint,
        action=ActivityLog.Action.NOTICE_GENERATED,
        target=complaint,
        summary=f"{title} generated for complaint '{complaint.title}'.",
        metadata={"notice_type": notice_type},
    )
    response = build_notice_pdf_response(request, complaint, title, lines, f"complaint-{complaint.pk}-{notice_type}.pdf")
    return response or redirect(complaint.get_absolute_url())


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
        "fee": "fee",
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
    fee_form = ComplaintFeeForm(
        request.POST if action == "fee" else None,
        instance=complaint,
        prefix="fee",
        can_finalize_fee=request.user.is_barangay_admin,
    )
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
                    "fee_form": fee_form,
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
            log_activity(
                actor=request.user,
                complaint=complaint,
                action=ActivityLog.Action.ASSIGNMENT_CHANGED,
                target=complaint.assigned_to,
                summary=f"Complaint '{complaint.title}' assigned to {complaint.assigned_to.get_full_name() or complaint.assigned_to.username}.",
                metadata={"old_assigned_to": old_assigned_to_id if (old_assigned_to_id := getattr(old_assigned_to, "id", None)) else None},
            )
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
        log_activity(
            actor=request.user,
            complaint=complaint,
            action=ActivityLog.Action.COMPLAINT_UPDATED,
            target=complaint,
            summary=f"Complaint '{complaint.title}' workflow updated.",
            metadata={"old_status": old_status, "new_status": complaint.status, "old_priority": old_priority, "new_priority": complaint.priority},
        )
        messages.success(request, "Complaint updated successfully.")
        return redirect(complaint.get_absolute_url())

    if request.method == "POST" and action == "fee":
        old_fee_status = complaint.fee_status
        if request.user.is_staff_member and complaint.fee_status in (Complaint.FeeStatus.PAID, Complaint.FeeStatus.WAIVED):
            messages.error(request, "Only admins can change a finalized filing fee record.")
            return redirect(complaint.get_absolute_url())
        if fee_form.is_valid():
            complaint = fee_form.save(commit=False)
            if complaint.fee_status == Complaint.FeeStatus.PAID:
                complaint.fee_collected_by = request.user
                if not complaint.fee_receipt_number:
                    complaint.fee_receipt_number = generate_fee_receipt_number(complaint)
            elif complaint.fee_status in (Complaint.FeeStatus.NOT_REQUIRED, Complaint.FeeStatus.PENDING):
                complaint.fee_receipt_number = ""
                complaint.fee_paid_at = None
                complaint.fee_collected_by = None
                if complaint.fee_status in (Complaint.FeeStatus.NOT_REQUIRED, Complaint.FeeStatus.PENDING):
                    complaint.fee_amount = None
            elif complaint.fee_status == Complaint.FeeStatus.WAIVED:
                complaint.fee_receipt_number = ""
                complaint.fee_paid_at = None
                complaint.fee_collected_by = None
            complaint.save(
                update_fields=[
                    "fee_status",
                    "fee_amount",
                    "fee_receipt_number",
                    "fee_paid_at",
                    "fee_collected_by",
                    "fee_notes",
                    "updated_at",
                ]
            )
            fee_messages = {
                Complaint.FeeStatus.PENDING: (
                    f"Your complaint '{complaint.title}' has a pending filing fee. "
                    "Please visit the barangay office for official payment and receipt."
                ),
                Complaint.FeeStatus.PAID: (
                    f"Your filing fee for complaint '{complaint.title}' has been recorded"
                    f"{' with OR No. ' + complaint.fee_receipt_number if complaint.fee_receipt_number else ''}."
                ),
                Complaint.FeeStatus.WAIVED: f"Your filing fee for complaint '{complaint.title}' has been waived.",
            }
            if complaint.fee_status != old_fee_status and complaint.fee_status in fee_messages:
                create_notification(
                    user=complaint.resident,
                    complaint=complaint,
                    message=fee_messages[complaint.fee_status],
                    notification_type=Notification.Type.STATUS_CHANGED,
                )
            log_activity(
                actor=request.user,
                complaint=complaint,
                action=ActivityLog.Action.FEE_UPDATED,
                target=complaint,
                summary=f"Filing fee changed from {old_fee_status} to {complaint.fee_status}.",
                metadata={"old_fee_status": old_fee_status, "new_fee_status": complaint.fee_status},
            )
            messages.success(request, "Filing fee record updated.")
            return redirect(complaint.get_absolute_url())

    if request.method == "POST" and action == "respondent" and respondent_form.is_valid():
        respondent_form.save()
        log_activity(
            actor=request.user,
            complaint=complaint,
            action=ActivityLog.Action.COMPLAINT_UPDATED,
            target=respondent,
            summary=f"Respondent details updated for complaint '{complaint.title}'.",
        )
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
        log_activity(
            actor=request.user,
            complaint=complaint,
            action=ActivityLog.Action.COMPLAINT_UPDATED,
            target=respondent,
            summary=f"Respondent contact recorded for complaint '{complaint.title}'.",
        )
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
            evidence = RespondentEvidence.objects.create(
                complaint=complaint,
                file=response_form.cleaned_data["evidence"],
                uploaded_by=request.user,
                evidence_type=RespondentEvidence.EvidenceType.RESPONSE,
                remarks=response_form.cleaned_data.get("evidence_remarks", ""),
                file_size=getattr(response_form.cleaned_data["evidence"], "size", 0) or 0,
                content_type=getattr(response_form.cleaned_data["evidence"], "content_type", "") or "",
            )
            log_activity(
                actor=request.user,
                complaint=complaint,
                action=ActivityLog.Action.EVIDENCE_UPLOADED,
                target=evidence,
                summary=f"Respondent evidence uploaded for complaint '{complaint.title}'.",
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
        log_activity(
            actor=request.user,
            complaint=complaint,
            action=ActivityLog.Action.COMPLAINT_UPDATED,
            target=response,
            summary=f"Respondent response recorded for complaint '{complaint.title}'.",
        )
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
        log_activity(
            actor=request.user,
            complaint=complaint,
            action=ActivityLog.Action.HEARING_SCHEDULED,
            target=hearing,
            summary=f"Hearing scheduled for complaint '{complaint.title}' on {hearing.date}.",
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
        log_activity(
            actor=request.user,
            complaint=complaint,
            action=ActivityLog.Action.COMPLAINT_UPDATED,
            target=hearing,
            summary=f"Hearing attendance/result recorded for complaint '{complaint.title}'.",
        )
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
        log_activity(
            actor=request.user,
            complaint=complaint,
            action=ActivityLog.Action.SECOND_NOTICE_RECORDED,
            target=complaint,
            summary=f"Second notice recorded for complaint '{complaint.title}'.",
        )
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
        log_activity(
            actor=request.user,
            complaint=complaint,
            action=ActivityLog.Action.ESCALATED,
            target=escalation,
            summary=f"Complaint '{complaint.title}' escalated to {escalation.escalated_to}.",
        )
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
            "fee_form": fee_form,
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
    status = request.GET.get("status", "")
    priority = request.GET.get("priority", "")
    category = request.GET.get("category", "")
    assigned_to = request.GET.get("assigned_to", "")
    fee_status = request.GET.get("fee_status", "")
    sla_status = request.GET.get("sla_status", "")
    purok = request.GET.get("purok", "").strip()
    response_status = request.GET.get("response_status", "")
    mediation_result = request.GET.get("mediation_result", "")
    if date_from:
        complaints = complaints.filter(created_at__date__gte=date_from)
    if date_to:
        complaints = complaints.filter(created_at__date__lte=date_to)
    if status:
        complaints = complaints.filter(status=status)
    if priority:
        complaints = complaints.filter(priority=priority)
    if category:
        complaints = complaints.filter(category_id=category)
    if assigned_to:
        complaints = complaints.filter(assigned_to_id=assigned_to)
    if fee_status:
        complaints = complaints.filter(fee_status=fee_status)
    if purok:
        complaints = complaints.filter(Q(incident_location__icontains=purok) | Q(resident__resident_profile__purok__icontains=purok))
    if response_status:
        complaints = complaints.filter(respondent__response_status=response_status)
    if mediation_result:
        complaints = complaints.filter(hearings__mediation_result=mediation_result)
    if sla_status == "overdue":
        complaints = complaints.filter(deadline_at__lt=timezone.now()).exclude(
            status__in=[
                Complaint.Status.RESOLVED,
                Complaint.Status.UNRESOLVED,
                Complaint.Status.ESCALATED,
                Complaint.Status.CLOSED,
                Complaint.Status.REJECTED,
            ]
        )
    elif sla_status == "on_track":
        complaints = complaints.filter(deadline_at__gte=timezone.now()).exclude(
            status__in=[
                Complaint.Status.RESOLVED,
                Complaint.Status.UNRESOLVED,
                Complaint.Status.ESCALATED,
                Complaint.Status.CLOSED,
                Complaint.Status.REJECTED,
            ]
        )
    elif sla_status == "closed":
        complaints = complaints.filter(
            status__in=[
                Complaint.Status.RESOLVED,
                Complaint.Status.UNRESOLVED,
                Complaint.Status.ESCALATED,
                Complaint.Status.CLOSED,
                Complaint.Status.REJECTED,
            ]
        )
    return complaints.distinct(), date_from, date_to


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
    staff_performance = []
    for person in staff_workload:
        assigned = complaints.filter(assigned_to=person)
        resolved = assigned.filter(status=Complaint.Status.RESOLVED)
        durations = [
            (item.resolved_at - item.created_at).total_seconds() / 3600
            for item in resolved
            if item.resolved_at
        ]
        active = assigned.filter(status__in=ACTIVE_ASSIGNMENT_STATUSES)
        staff_performance.append(
            {
                "user": person,
                "assigned": assigned.count(),
                "active": active.count(),
                "resolved": resolved.count(),
                "overdue": sum(1 for item in active if item.is_overdue),
                "average_resolution_hours": round(sum(durations) / len(durations), 1) if durations else 0,
            }
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
    feedback_summary = ComplaintFeedback.objects.filter(complaint__in=complaints).aggregate(
        total=Count("id"),
        average_rating=Avg("rating"),
    )
    accepted_feedback_count = ComplaintFeedback.objects.filter(complaint__in=complaints, resolution_accepted=True).count()
    return render(
        request,
        "complaints/reports.html",
        {
            "by_status": by_status,
            "by_category": by_category,
            "staff_workload": staff_workload,
            "staff_performance": staff_performance,
            "total_complaints": total_complaints,
            "resolved_count": resolved_count,
            "pending_count": pending_count,
            "overdue_count": overdue_count,
            "average_resolution_hours": average_resolution_hours,
            "by_location": by_location,
            "date_from": request.GET.get("date_from", ""),
            "date_to": request.GET.get("date_to", ""),
            "query_string": request.GET.urlencode(),
            "status_choices": Complaint.Status.choices,
            "priority_choices": Complaint.Priority.choices,
            "fee_status_choices": Complaint.FeeStatus.choices,
            "category_choices": ComplaintCategory.objects.filter(is_active=True).order_by("name"),
            "staff_choices": User.objects.filter(role=User.Role.STAFF, is_active=True).order_by("last_name", "first_name"),
            "response_status_choices": Respondent.ResponseStatus.choices,
            "mediation_result_choices": HearingMediation.MediationResult.choices,
            "selected_status": request.GET.get("status", ""),
            "selected_priority": request.GET.get("priority", ""),
            "selected_category": request.GET.get("category", ""),
            "selected_assigned_to": request.GET.get("assigned_to", ""),
            "selected_fee_status": request.GET.get("fee_status", ""),
            "selected_sla_status": request.GET.get("sla_status", ""),
            "selected_purok": request.GET.get("purok", ""),
            "selected_response_status": request.GET.get("response_status", ""),
            "selected_mediation_result": request.GET.get("mediation_result", ""),
            "feedback_count": feedback_summary["total"] or 0,
            "average_feedback_rating": round(feedback_summary["average_rating"], 1) if feedback_summary["average_rating"] else 0,
            "accepted_feedback_count": accepted_feedback_count,
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
