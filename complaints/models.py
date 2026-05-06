from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class ComplaintCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    default_priority = models.CharField(
        max_length=20,
        choices=[("LOW", "Low"), ("NORMAL", "Normal"), ("HIGH", "High"), ("URGENT", "Urgent")],
        default="NORMAL",
    )
    target_resolution_hours = models.PositiveIntegerField(default=72)
    responsible_department = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=20, blank=True, help_text="Optional dashboard color such as #2563eb.")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Complaint categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Complaint(models.Model):
    SLA_HOURS = {
        "LOW": 168,
        "NORMAL": 72,
        "HIGH": 48,
        "URGENT": 24,
    }

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Review"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        RESPONDENT_NOT_CONTACTED = "RESPONDENT_NOT_CONTACTED", "Respondent Not Contacted"
        RESPONDENT_CONTACTED = "RESPONDENT_CONTACTED", "Respondent Contacted"
        WAITING_RESPONDENT_RESPONSE = "WAITING_RESPONDENT_RESPONSE", "Waiting for Respondent Response"
        RESPONDENT_RESPONSE_RECORDED = "RESPONDENT_RESPONSE_RECORDED", "Respondent Response Recorded"
        NO_RESPONSE = "NO_RESPONSE", "No Response"
        FAILED_TO_ATTEND = "FAILED_TO_ATTEND", "Failed to Attend"
        SECOND_NOTICE_SENT = "SECOND_NOTICE_SENT", "Second Notice Sent"
        HEARING_SCHEDULED = "HEARING_SCHEDULED", "Hearing Scheduled"
        IN_MEDIATION = "IN_MEDIATION", "In Mediation"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        UNRESOLVED = "UNRESOLVED", "Unresolved"
        ESCALATED = "ESCALATED", "Escalated"
        CLOSED = "CLOSED", "Closed"
        REJECTED = "REJECTED", "Rejected"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class FeeStatus(models.TextChoices):
        NOT_REQUIRED = "NOT_REQUIRED", "Not Required"
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        WAIVED = "WAIVED", "Waived"

    resident = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
    )
    category = models.ForeignKey(ComplaintCategory, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=150)
    description = models.TextField()
    contact_number = models.CharField(max_length=20, blank=True, verbose_name="Contact Number")
    incident_location = models.CharField(max_length=255)
    incident_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.PENDING)
    privacy_consent = models.BooleanField(default=False)
    accuracy_certification = models.BooleanField(default=False)
    contact_permission = models.BooleanField(default=False)
    consented_at = models.DateTimeField(null=True, blank=True)
    public_remarks = models.TextField(blank=True)
    internal_remarks = models.TextField(blank=True)
    fee_status = models.CharField(max_length=20, choices=FeeStatus.choices, default=FeeStatus.NOT_REQUIRED)
    fee_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fee_receipt_number = models.CharField(max_length=80, blank=True)
    fee_paid_at = models.DateField(null=True, blank=True)
    fee_collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collected_complaint_fees",
    )
    fee_notes = models.TextField(blank=True)
    second_notice_sent = models.BooleanField(default=False)
    second_notice_date = models.DateField(null=True, blank=True)
    second_notice_method = models.CharField(max_length=50, blank=True)
    second_notice_remarks = models.TextField(blank=True)
    deadline_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse("complaints:detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.deadline_at:
            self.set_deadline()
        super().save(*args, **kwargs)

    def get_sla_hours(self):
        return self.SLA_HOURS.get(self.priority, self.SLA_HOURS[self.Priority.NORMAL])

    def set_deadline(self, reference_time=None):
        reference_time = reference_time or self.created_at or timezone.now()
        self.deadline_at = reference_time + timedelta(hours=self.get_sla_hours())

    @property
    def is_priority_urgent(self):
        return self.priority == self.Priority.URGENT

    @property
    def is_closed(self):
        return self.status in [
            self.Status.RESOLVED,
            self.Status.UNRESOLVED,
            self.Status.ESCALATED,
            self.Status.CLOSED,
            self.Status.REJECTED,
        ]

    @property
    def is_overdue(self):
        return bool(self.deadline_at and not self.is_closed and self.deadline_at < timezone.now())

    @property
    def sla_label(self):
        if self.is_closed:
            return "Closed"
        if self.is_overdue:
            return "Overdue"
        return "On track"


class ComplaintStatusHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=40, choices=Complaint.Status.choices, blank=True)
    new_status = models.CharField(max_length=40, choices=Complaint.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True)
    public_remarks = models.TextField(blank=True)
    internal_remarks = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name_plural = "Complaint status history"

    def __str__(self):
        old_status = self.old_status or "New"
        return f"{self.complaint.title}: {old_status} to {self.new_status}"


class UploadedEvidence(models.Model):
    class EvidenceType(models.TextChoices):
        INITIAL = "INITIAL", "Initial Evidence"
        FOLLOW_UP = "FOLLOW_UP", "Follow-up Evidence"
        INSPECTION = "INSPECTION", "Inspection Photo"
        RESOLUTION = "RESOLUTION", "Resolution Proof"
        OTHER = "OTHER", "Other"

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="evidence_files")
    file = models.FileField(upload_to="complaint_uploads/")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    evidence_type = models.CharField(max_length=20, choices=EvidenceType.choices, default=EvidenceType.INITIAL)
    description = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence for {self.complaint.title}"


class Respondent(models.Model):
    class ContactMethod(models.TextChoices):
        CALL = "CALL", "Call"
        LETTER = "LETTER", "Letter"
        EMAIL = "EMAIL", "Email"
        PERSONAL_NOTICE = "PERSONAL_NOTICE", "Personal Notice"
        OTHER = "OTHER", "Other"

    class ResponseStatus(models.TextChoices):
        WAITING = "WAITING", "Waiting"
        RESPONDED = "RESPONDED", "Responded"
        NO_RESPONSE = "NO_RESPONSE", "No Response"
        FAILED_TO_ATTEND = "FAILED_TO_ATTEND", "Failed to Attend"

    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="respondent")
    full_name = models.CharField(max_length=150, default="Unknown")
    contact_number = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True, verbose_name="Address or Purok")
    email = models.EmailField(blank=True)
    relationship_to_complainant = models.CharField(max_length=100, blank=True)
    is_known_to_complainant = models.BooleanField(default=True)
    identifying_details = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    contacted = models.BooleanField(default=False)
    contact_method = models.CharField(max_length=30, choices=ContactMethod.choices, blank=True)
    contact_date = models.DateField(null=True, blank=True)
    contacted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="respondent_contacts",
    )
    contact_remarks = models.TextField(blank=True)
    response_status = models.CharField(max_length=30, choices=ResponseStatus.choices, default=ResponseStatus.WAITING)
    response_statement = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} for {self.complaint.title}"


class ComplaintResponse(models.Model):
    class Source(models.TextChoices):
        STAFF = "STAFF", "Staff Remarks"
        RESPONDENT = "RESPONDENT", "Respondent Response"

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="responses")
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    remarks = models.TextField()
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.STAFF)
    is_public = models.BooleanField(default=True)
    status_after_response = models.CharField(max_length=40, choices=Complaint.Status.choices, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Response for {self.complaint.title}"


class RespondentEvidence(models.Model):
    class EvidenceType(models.TextChoices):
        RESPONDENT = "RESPONDENT", "Respondent Evidence"
        RESPONSE = "RESPONSE", "Response Attachment"
        OTHER = "OTHER", "Other"

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="respondent_evidence_files")
    file = models.FileField(upload_to="respondent_uploads/")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    evidence_type = models.CharField(max_length=20, choices=EvidenceType.choices, default=EvidenceType.RESPONDENT)
    remarks = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Respondent evidence for {self.complaint.title}"


class ComplaintReply(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    attachment = models.FileField(upload_to="complaint_replies/", null=True, blank=True)
    attachment_size = models.PositiveIntegerField(default=0)
    attachment_content_type = models.CharField(max_length=100, blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply for {self.complaint.title}"


class HearingMediation(models.Model):
    class MediationResult(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RESOLVED = "RESOLVED", "Resolved"
        UNRESOLVED = "UNRESOLVED", "Unresolved"
        RESCHEDULED = "RESCHEDULED", "Rescheduled"
        FOR_ESCALATION = "FOR_ESCALATION", "For Escalation"

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="hearings")
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=255)
    purpose = models.CharField(max_length=255)
    remarks = models.TextField(blank=True, verbose_name="Remarks or instructions")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    complainant_attended = models.BooleanField(default=False)
    respondent_attended = models.BooleanField(default=False)
    attendance_recorded = models.BooleanField(default=False)
    attendance_remarks = models.TextField(blank=True)
    mediation_result = models.CharField(
        max_length=30,
        choices=MediationResult.choices,
        default=MediationResult.PENDING,
    )
    agreement_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"{self.purpose} for {self.complaint.title} on {self.date}"


class Escalation(models.Model):
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="escalation")
    escalated = models.BooleanField(default=True)
    escalation_date = models.DateField(default=timezone.localdate)
    escalated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    escalated_to = models.CharField(max_length=150)
    reason = models.TextField(verbose_name="Reason for escalation")
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Escalation for {self.complaint.title}"


class Notification(models.Model):
    class Type(models.TextChoices):
        GENERAL = "GENERAL", "General"
        SUBMITTED = "SUBMITTED", "Complaint Submitted"
        ASSIGNED = "ASSIGNED", "Complaint Assigned"
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"
        REMARKS_ADDED = "REMARKS_ADDED", "Remarks Added"
        OVERDUE = "OVERDUE", "Overdue"

    class DeliveryStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Skipped"
        NOT_CONFIGURED = "NOT_CONFIGURED", "Not Configured"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=30, choices=Type.choices, default=Type.GENERAL)
    title = models.CharField(max_length=150, blank=True)
    message = models.TextField()
    link_target = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    email_status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message
