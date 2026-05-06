import sys
from copy import copy

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.template.context import BaseContext, Context, RequestContext
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import ResidentProfile, StaffProfile, User
from .models import ActivityLog, Complaint, ComplaintCategory, ComplaintFeedback, Notification, Respondent, UploadedEvidence


if sys.version_info >= (3, 14):
    def _copy_template_context(context):
        duplicate = object.__new__(context.__class__)
        duplicate.__dict__.update(context.__dict__)
        duplicate.dicts = context.dicts[:]
        if hasattr(context, "render_context"):
            duplicate.render_context = copy(context.render_context)
        return duplicate

    BaseContext.__copy__ = _copy_template_context
    Context.__copy__ = _copy_template_context
    RequestContext.__copy__ = _copy_template_context


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
        self.assertTrue(
            Notification.objects.filter(
                user=self.resident,
                complaint=self.complaint,
                notification_type=Notification.Type.ASSIGNED,
                message__contains=self.new_staff.username,
            ).exists()
        )

    def test_admin_records_paid_filing_fee_and_notifies_resident(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("complaints:update", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "fee",
                "fee-fee_status": Complaint.FeeStatus.PAID,
                "fee-fee_amount": "50.00",
                "fee-fee_paid_at": timezone.localdate().isoformat(),
                "fee-fee_notes": "Official receipt issued.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.fee_status, Complaint.FeeStatus.PAID)
        self.assertEqual(str(self.complaint.fee_amount), "50.00")
        self.assertEqual(self.complaint.fee_receipt_number, f"FEE-{timezone.localdate().year}-CMP{self.complaint.pk:05d}")
        self.assertEqual(self.complaint.fee_collected_by, self.admin)
        self.assertTrue(
            Notification.objects.filter(
                user=self.resident,
                complaint=self.complaint,
                message__contains=self.complaint.fee_receipt_number,
            ).exists()
        )

    def test_staff_can_only_mark_filing_fee_pending(self):
        self.client.force_login(self.old_staff)

        response = self.client.post(
            reverse("complaints:update", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "fee",
                "fee-fee_status": Complaint.FeeStatus.PENDING,
                "fee-fee_notes": "Resident should be advised at intake.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.fee_status, Complaint.FeeStatus.PENDING)
        self.assertIsNone(self.complaint.fee_amount)
        self.assertEqual(self.complaint.fee_receipt_number, "")

        response = self.client.post(
            reverse("complaints:update", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "fee",
                "fee-fee_status": Complaint.FeeStatus.PAID,
                "fee-fee_amount": "50.00",
                "fee-fee_paid_at": timezone.localdate().isoformat(),
                "fee-fee_notes": "Trying to finalize as staff.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.fee_status, Complaint.FeeStatus.PENDING)
        self.assertEqual(self.complaint.fee_receipt_number, "")

    def test_staff_cannot_change_finalized_filing_fee(self):
        self.complaint.fee_status = Complaint.FeeStatus.PAID
        self.complaint.fee_amount = "50.00"
        self.complaint.fee_receipt_number = f"FEE-{timezone.localdate().year}-CMP{self.complaint.pk:05d}"
        self.complaint.fee_paid_at = timezone.localdate()
        self.complaint.fee_collected_by = self.admin
        self.complaint.save()
        self.client.force_login(self.old_staff)

        response = self.client.post(
            reverse("complaints:update", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "fee",
                "fee-fee_status": Complaint.FeeStatus.PENDING,
                "fee-fee_notes": "Trying to reopen as staff.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.fee_status, Complaint.FeeStatus.PAID)
        self.assertTrue(self.complaint.fee_receipt_number.startswith("FEE-"))

    def test_waived_filing_fee_requires_reason_and_notifies_resident(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("complaints:update", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "fee",
                "fee-fee_status": Complaint.FeeStatus.WAIVED,
                "fee-fee_amount": "",
                "fee-fee_receipt_number": "",
                "fee-fee_paid_at": "",
                "fee-fee_notes": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add a short waiver reason.")

        response = self.client.post(
            reverse("complaints:update", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "fee",
                "fee-fee_status": Complaint.FeeStatus.WAIVED,
                "fee-fee_amount": "",
                "fee-fee_receipt_number": "",
                "fee-fee_paid_at": "",
                "fee-fee_notes": "Indigent complainant.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.fee_status, Complaint.FeeStatus.WAIVED)
        self.assertEqual(self.complaint.fee_notes, "Indigent complainant.")
        self.assertTrue(
            Notification.objects.filter(
                user=self.resident,
                complaint=self.complaint,
                message__contains="has been waived",
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

    def test_resident_detail_does_not_auto_clear_unread_notifications(self):
        notification = Notification.objects.create(
            user=self.resident,
            complaint=self.complaint,
            message="Your complaint status was updated.",
            notification_type=Notification.Type.STATUS_CHANGED,
        )
        self.client.force_login(self.resident)

        response = self.client.get(reverse("complaints:detail", kwargs={"pk": self.complaint.pk}))

        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_notification_view_marks_single_notification_read_and_redirects(self):
        notification = Notification.objects.create(
            user=self.resident,
            complaint=self.complaint,
            message="Your complaint status was updated.",
            notification_type=Notification.Type.STATUS_CHANGED,
        )
        other_notification = Notification.objects.create(
            user=self.resident,
            complaint=self.complaint,
            message="Another update.",
            notification_type=Notification.Type.REMARKS_ADDED,
        )
        self.client.force_login(self.resident)

        response = self.client.get(reverse("complaints:notification_view", kwargs={"pk": notification.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.complaint.get_absolute_url())
        notification.refresh_from_db()
        other_notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
        self.assertFalse(other_notification.is_read)

    def test_unverified_resident_cannot_open_submit_complaint(self):
        self.resident.resident_profile.verification_status = ResidentProfile.VerificationStatus.UNVERIFIED
        self.resident.resident_profile.save(update_fields=["verification_status"])
        self.client.force_login(self.resident)

        response = self.client.get(reverse("complaints:submit"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("accounts:profile"))

    def test_verified_resident_can_open_submit_complaint(self):
        self.resident.resident_profile.verification_status = ResidentProfile.VerificationStatus.VERIFIED
        self.resident.resident_profile.save(update_fields=["verification_status"])
        self.client.force_login(self.resident)

        response = self.client.get(reverse("complaints:submit"))

        self.assertEqual(response.status_code, 200)

    def test_staff_can_review_uploaded_evidence(self):
        evidence = UploadedEvidence.objects.create(
            complaint=self.complaint,
            uploaded_by=self.resident,
            file=SimpleUploadedFile("proof.txt", b"proof", content_type="text/plain"),
        )
        self.client.force_login(self.old_staff)

        response = self.client.post(
            reverse("complaints:detail", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "evidence_review",
                "evidence_kind": "complainant",
                "evidence_id": str(evidence.pk),
                "review_status": UploadedEvidence.ReviewStatus.ACCEPTED,
                "review_remarks": "Readable and relevant.",
            },
        )

        self.assertEqual(response.status_code, 302)
        evidence.refresh_from_db()
        self.assertEqual(evidence.review_status, UploadedEvidence.ReviewStatus.ACCEPTED)
        self.assertEqual(evidence.reviewed_by, self.old_staff)
        self.assertTrue(ActivityLog.objects.filter(action=ActivityLog.Action.EVIDENCE_REVIEWED).exists())

    def test_resident_can_submit_feedback_after_resolution(self):
        self.complaint.status = Complaint.Status.RESOLVED
        self.complaint.resolved_at = timezone.now()
        self.complaint.save(update_fields=["status", "resolved_at"])
        self.client.force_login(self.resident)

        response = self.client.post(
            reverse("complaints:detail", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "feedback",
                "rating": "5",
                "resolution_accepted": "on",
                "comments": "Handled well.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(ComplaintFeedback.objects.filter(complaint=self.complaint, rating=5).exists())

    def test_reports_filter_by_fee_status(self):
        self.complaint.fee_status = Complaint.FeeStatus.PAID
        self.complaint.save(update_fields=["fee_status"])
        other = Complaint.objects.create(
            resident=self.resident,
            category=self.category,
            title="Other issue",
            description="Another complaint.",
            incident_location="Purok Test",
            incident_date=timezone.localdate(),
            privacy_consent=True,
            accuracy_certification=True,
            contact_permission=True,
            fee_status=Complaint.FeeStatus.PENDING,
        )
        Respondent.objects.create(complaint=other, full_name="Other respondent")
        self.client.force_login(self.admin)

        response = self.client.get(reverse("complaints:reports"), {"fee_status": Complaint.FeeStatus.PAID})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_complaints"], 1)

    def test_staff_can_generate_resolution_summary_pdf(self):
        self.client.force_login(self.old_staff)

        response = self.client.get(
            reverse("complaints:notice_pdf", kwargs={"pk": self.complaint.pk, "notice_type": "summary"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(ActivityLog.objects.filter(action=ActivityLog.Action.NOTICE_GENERATED).exists())

    def test_check_sla_command_notifies_overdue_complaints(self):
        self.complaint.deadline_at = timezone.now() - timezone.timedelta(hours=2)
        self.complaint.save(update_fields=["deadline_at"])

        call_command("check_sla")

        self.assertTrue(
            Notification.objects.filter(
                complaint=self.complaint,
                notification_type=Notification.Type.OVERDUE,
            ).exists()
        )
        self.assertTrue(ActivityLog.objects.filter(action=ActivityLog.Action.SLA_OVERDUE_FLAGGED).exists())
