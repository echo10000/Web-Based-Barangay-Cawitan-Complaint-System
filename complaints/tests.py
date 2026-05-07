from unittest.mock import patch

from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import ActivityLog, Complaint, ComplaintFeedback
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
