from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import ResidentProfile, StaffProfile, User
from .models import Complaint, ComplaintCategory, Notification, Respondent


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST_USER="test@example.com",
    DEFAULT_FROM_EMAIL="test@example.com",
)
class ComplaintNotificationTests(TestCase):
    def setUp(self):
        self.category = ComplaintCategory.objects.create(name="Noise", is_active=True)
        self.resident = User.objects.create_user(
            username="resident",
            password="Pass12345!",
            email="resident@example.com",
            role=User.Role.RESIDENT,
        )
        ResidentProfile.objects.create(
            user=self.resident,
            phone_number="09170000001",
            address="Purok Test",
        )
        self.old_staff = User.objects.create_user(
            username="old_staff",
            password="Pass12345!",
            email="old-staff@example.com",
            role=User.Role.STAFF,
            is_staff=True,
        )
        StaffProfile.objects.create(user=self.old_staff, phone_number="09170000002")
        self.new_staff = User.objects.create_user(
            username="new_staff",
            password="Pass12345!",
            email="new-staff@example.com",
            role=User.Role.STAFF,
            is_staff=True,
        )
        StaffProfile.objects.create(user=self.new_staff, phone_number="09170000003")
        self.admin = User.objects.create_user(
            username="admin",
            password="Pass12345!",
            email="admin@example.com",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.complaint = Complaint.objects.create(
            resident=self.resident,
            assigned_to=self.old_staff,
            category=self.category,
            title="Loud karaoke",
            description="Late night noise complaint.",
            incident_location="Purok Test",
            incident_date=timezone.localdate(),
            privacy_consent=True,
            accuracy_certification=True,
            contact_permission=True,
        )
        Respondent.objects.create(complaint=self.complaint, full_name="Respondent")

    def test_admin_complaint_update_notifies_status_change_and_new_assignee(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("complaints:update", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "complaint",
                "complaint-category": str(self.category.pk),
                "complaint-priority": Complaint.Priority.HIGH,
                "complaint-status": Complaint.Status.UNDER_REVIEW,
                "complaint-assigned_to": str(self.new_staff.pk),
                "complaint-public_remarks_input": "We are reviewing this complaint.",
                "complaint-internal_remarks_input": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.complaint.get_absolute_url())
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, Complaint.Status.UNDER_REVIEW)
        self.assertEqual(self.complaint.assigned_to, self.new_staff)
        self.assertTrue(
            Notification.objects.filter(
                user=self.resident,
                complaint=self.complaint,
                notification_type=Notification.Type.STATUS_CHANGED,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.new_staff,
                complaint=self.complaint,
                notification_type=Notification.Type.ASSIGNED,
            ).exists()
        )

    def test_resident_follow_up_notifies_admin_and_assignee(self):
        self.client.force_login(self.resident)

        response = self.client.post(
            reverse("complaints:detail", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "reply",
                "message": "Here is an extra detail about the complaint.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.complaint.get_absolute_url())
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin,
                complaint=self.complaint,
                notification_type=Notification.Type.REMARKS_ADDED,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.old_staff,
                complaint=self.complaint,
                notification_type=Notification.Type.REMARKS_ADDED,
            ).exists()
        )
