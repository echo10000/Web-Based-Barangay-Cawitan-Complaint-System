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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="resident_profile")
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255)
    birth_date = models.DateField(null=True, blank=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Password reset OTP for {self.user.username}"

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)
