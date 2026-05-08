from unittest.mock import patch
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from accounts.models import DataExportRequest, User
from .models import ActivityLog, Complaint, ComplaintFeedback, UploadedEvidence
from .views import complaint_detail_view


class ComplaintFeedbackViewTests(TestCase):
    def setUp(self):
        self.resident = User.objects.create_user(
            username="resident",
            password="password123",
            role=User.Role.RESIDENT,
        )
        self.other_resident = User.objects.create_user(
            username="other-resident",
            password="password123",
            role=User.Role.RESIDENT,
        )
        self.complaint = Complaint.objects.create(
            resident=self.resident,
            title="Streetlight issue",
            description="Streetlight is not working.",
            incident_location="Purok 1",
            privacy_consent=True,
            accuracy_certification=True,
            contact_permission=True,
            status=Complaint.Status.RESOLVED,
        )

    def assertRedirectToComplaint(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.complaint.get_absolute_url())

    def test_resident_can_submit_feedback_for_resolved_complaint(self):
        self.client.force_login(self.resident)

        response = self.client.post(
            reverse("complaints:detail", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "feedback",
                "rating": "4",
                "resolution_accepted": "true",
                "comments": "Handled well.",
            },
        )

        self.assertRedirectToComplaint(response)
        feedback = ComplaintFeedback.objects.get(complaint=self.complaint)
        self.assertEqual(feedback.resident, self.resident)
        self.assertEqual(feedback.rating, 4)
        self.assertTrue(feedback.resolution_accepted)
        self.assertEqual(feedback.comments, "Handled well.")
        self.assertTrue(
            ActivityLog.objects.filter(
                complaint=self.complaint,
                action=ActivityLog.Action.FEEDBACK_SUBMITTED,
            ).exists()
        )

    def test_resident_can_decline_resolution_in_feedback(self):
        self.client.force_login(self.resident)

        self.client.post(
            reverse("complaints:detail", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "feedback",
                "rating": "2",
                "resolution_accepted": "false",
                "comments": "The issue is still happening.",
            },
        )

        feedback = ComplaintFeedback.objects.get(complaint=self.complaint)
        self.assertFalse(feedback.resolution_accepted)

    def test_other_resident_cannot_submit_feedback(self):
        self.client.force_login(self.other_resident)

        response = self.client.post(
            reverse("complaints:detail", kwargs={"pk": self.complaint.pk}),
            {
                "workflow_action": "feedback",
                "rating": "5",
                "resolution_accepted": "true",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("complaints:list"))
        self.assertFalse(ComplaintFeedback.objects.exists())

    def test_feedback_requires_explicit_acceptance_choice(self):
        request = RequestFactory().post(
            reverse("complaints:detail", kwargs={"pk": self.complaint.pk}),
            data={
                "workflow_action": "feedback",
                "rating": "3",
                "comments": "No acceptance choice yet.",
            },
        )
        request.user = self.resident

        with patch("complaints.views.render") as mock_render:
            mock_render.return_value.status_code = 200
            complaint_detail_view(request, self.complaint.pk)

        context = mock_render.call_args.args[2]
        self.assertTrue(context["feedback_form"].is_bound)
        self.assertIn("resolution_accepted", context["feedback_form"].errors)
        self.assertFalse(ComplaintFeedback.objects.exists())

    def test_feedback_requires_rating(self):
        request = RequestFactory().post(
            reverse("complaints:detail", kwargs={"pk": self.complaint.pk}),
            data={
                "workflow_action": "feedback",
                "resolution_accepted": "true",
            },
        )
        request.user = self.resident

        with patch("complaints.views.render") as mock_render:
            mock_render.return_value.status_code = 200
            complaint_detail_view(request, self.complaint.pk)

        context = mock_render.call_args.args[2]
        self.assertIn("rating", context["feedback_form"].errors)
        self.assertFalse(ComplaintFeedback.objects.exists())

    def test_feedback_rejects_out_of_range_rating(self):
        request = RequestFactory().post(
            reverse("complaints:detail", kwargs={"pk": self.complaint.pk}),
            data={
                "workflow_action": "feedback",
                "rating": "6",
                "resolution_accepted": "true",
            },
        )
        request.user = self.resident

        with patch("complaints.views.render") as mock_render:
            mock_render.return_value.status_code = 200
            complaint_detail_view(request, self.complaint.pk)

        context = mock_render.call_args.args[2]
        self.assertIn("rating", context["feedback_form"].errors)
        self.assertFalse(ComplaintFeedback.objects.exists())

    def test_feedback_rejects_invalid_acceptance_value(self):
        request = RequestFactory().post(
            reverse("complaints:detail", kwargs={"pk": self.complaint.pk}),
            data={
                "workflow_action": "feedback",
                "rating": "4",
                "resolution_accepted": "maybe",
            },
        )
        request.user = self.resident

        with patch("complaints.views.render") as mock_render:
            mock_render.return_value.status_code = 200
            complaint_detail_view(request, self.complaint.pk)

        context = mock_render.call_args.args[2]
        self.assertIn("resolution_accepted", context["feedback_form"].errors)
        self.assertFalse(ComplaintFeedback.objects.exists())

    def test_feedback_rejects_comments_over_300_characters(self):
        request = RequestFactory().post(
            reverse("complaints:detail", kwargs={"pk": self.complaint.pk}),
            data={
                "workflow_action": "feedback",
                "rating": "4",
                "resolution_accepted": "true",
                "comments": "x" * 301,
            },
        )
        request.user = self.resident

        with patch("complaints.views.render") as mock_render:
            mock_render.return_value.status_code = 200
            complaint_detail_view(request, self.complaint.pk)

        context = mock_render.call_args.args[2]
        self.assertIn("comments", context["feedback_form"].errors)
        self.assertFalse(ComplaintFeedback.objects.exists())

    def test_feedback_form_is_not_bound_by_other_detail_actions(self):
        request = RequestFactory().get(reverse("complaints:detail", kwargs={"pk": self.complaint.pk}))
        request.user = self.resident

        with patch("complaints.views.render") as mock_render:
            mock_render.return_value.status_code = 200
            complaint_detail_view(request, self.complaint.pk)

        context = mock_render.call_args.args[2]
        self.assertFalse(context["feedback_form"].is_bound)
        self.assertTrue(context["can_submit_feedback"])
        self.assertIsNone(context["existing_feedback"])


class ComplaintPrivacyControlTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="password123",
            role=User.Role.ADMIN,
        )
        self.resident = User.objects.create_user(
            username="resident",
            password="password123",
            role=User.Role.RESIDENT,
        )
        self.other_resident = User.objects.create_user(
            username="other-resident",
            password="password123",
            role=User.Role.RESIDENT,
        )
        self.complaint = Complaint.objects.create(
            resident=self.resident,
            title="Drainage issue",
            description="Canal is clogged.",
            incident_location="Purok 2",
            privacy_consent=True,
            accuracy_certification=True,
            contact_permission=True,
        )

    def test_report_export_requires_approved_request(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("complaints:reports_export_xlsx"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("complaints:reports"))
        self.assertFalse(ActivityLog.objects.filter(action=ActivityLog.Action.DATA_EXPORTED).exists())

    def test_approved_export_request_must_match_filters(self):
        export_request = DataExportRequest.objects.create(
            export_type=DataExportRequest.ExportType.COMPLAINT_XLSX,
            purpose="OFFICIAL_MONITORING",
            reason="Official monitoring for monthly case status.",
            filters={"status": Complaint.Status.PENDING},
            requested_by=self.admin,
            approved_by=User.objects.create_superuser(username="super", password="password123"),
            status=DataExportRequest.Status.APPROVED,
        )
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("complaints:reports_export_xlsx"),
            {"status": Complaint.Status.RESOLVED, "export_request": export_request.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("complaints:reports"))
        export_request.refresh_from_db()
        self.assertEqual(export_request.status, DataExportRequest.Status.APPROVED)

    def test_unrelated_resident_cannot_open_evidence_file(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            evidence = UploadedEvidence.objects.create(
                complaint=self.complaint,
                uploaded_by=self.resident,
                file=SimpleUploadedFile("proof.txt", b"private evidence", content_type="text/plain"),
            )
            self.client.force_login(self.other_resident)

            response = self.client.get(reverse("complaints:file", kwargs={"kind": "evidence", "pk": evidence.pk}))

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response["Location"], reverse("complaints:list"))
            self.assertFalse(
                ActivityLog.objects.filter(action=ActivityLog.Action.SENSITIVE_FILE_VIEWED, target_id=evidence.pk).exists()
            )
