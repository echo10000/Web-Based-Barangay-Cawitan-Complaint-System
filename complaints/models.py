from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class ComplaintCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
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
        PENDING = "PENDING", "Pending"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        REJECTED = "REJECTED", "Rejected"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

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
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
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
        return self.status in [self.Status.RESOLVED, self.Status.REJECTED]

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
    old_status = models.CharField(max_length=20, choices=Complaint.Status.choices, blank=True)
    new_status = models.CharField(max_length=20, choices=Complaint.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name_plural = "Complaint status history"

    def __str__(self):
        old_status = self.old_status or "New"
        return f"{self.complaint.title}: {old_status} to {self.new_status}"


class UploadedEvidence(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="evidence_files")
    file = models.FileField(upload_to="complaint_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence for {self.complaint.title}"


class ComplaintResponse(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="responses")
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    remarks = models.TextField()
    status_after_response = models.CharField(max_length=20, choices=Complaint.Status.choices, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Response for {self.complaint.title}"


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
    message = models.CharField(max_length=255)
    link_target = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    email_status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_error = models.TextField(blank=True)
    sms_status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    sms_sent_at = models.DateTimeField(null=True, blank=True)
    sms_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message
