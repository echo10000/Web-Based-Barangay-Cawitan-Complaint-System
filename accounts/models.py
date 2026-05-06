from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        RESIDENT = "RESIDENT", "Resident"
        STAFF = "STAFF", "Barangay Staff"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RESIDENT)

    @property
    def is_resident(self):
        return self.role == self.Role.RESIDENT

    @property
    def is_staff_member(self):
        return self.role == self.Role.STAFF

    @property
    def is_barangay_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser


class ResidentProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "UNVERIFIED", "Unverified"
        PENDING = "PENDING", "Pending Verification"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="resident_profile")
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255)
    purok = models.CharField(max_length=100, blank=True)
    household_number = models.CharField(max_length=50, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    valid_id_front_image = models.ImageField(upload_to="resident_ids/", null=True, blank=True)
    valid_id_back_image = models.ImageField(upload_to="resident_ids/", null=True, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )
    verification_notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_residents",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class StaffProfile(models.Model):
    class Availability(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        BUSY = "BUSY", "Busy"
        UNAVAILABLE = "UNAVAILABLE", "Unavailable"

    DEFAULT_RESPONSIBILITIES = "\n".join(
        [
            "Receive and review complaints",
            "Categorize complaints by type and urgency",
            "Assign or forward complaints to the correct handler",
            "Update complaint status and internal notes",
            "Communicate updates to complainants",
            "Upload evidence, inspection notes, or resolution proof",
            "Monitor overdue and urgent complaints",
            "Prepare complaint summaries and reports",
        ]
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    position = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    availability = models.CharField(max_length=20, choices=Availability.choices, default=Availability.AVAILABLE)
    specialization_categories = models.ManyToManyField(
        "complaints.ComplaintCategory",
        blank=True,
        related_name="specialized_staff_profiles",
    )
    phone_number = models.CharField(max_length=20, blank=True)
    responsibilities = models.TextField(default=DEFAULT_RESPONSIBILITIES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.position or 'Staff'}"


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="password_reset_otps")
    otp = models.CharField(max_length=6)
    otp_hash = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    resend_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Password reset OTP for {self.user.username}"

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)
