from unittest.mock import patch
from uuid import uuid4

from django.http import HttpResponse
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from complaints.models import Complaint, ComplaintCategory
from .views import admin_dashboard_view


class AdminDashboardChartDataTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        suffix = uuid4().hex[:8]
        self.admin = User.objects.create_user(
            username=f"admin-{suffix}",
            password="password123",
            role=User.Role.ADMIN,
        )
        self.resident = User.objects.create_user(
            username=f"resident-{suffix}",
            password="password123",
            role=User.Role.RESIDENT,
        )
        self.category = ComplaintCategory.objects.create(name=f"Street Lighting {suffix}")
        Complaint.objects.create(
            resident=self.resident,
            category=self.category,
            title="Broken streetlight",
            description="The streetlight is out.",
            incident_location="Purok 1",
            privacy_consent=True,
            accuracy_certification=True,
            contact_permission=True,
        )

    def test_chart_context_uses_objects_not_json_strings(self):
        request = self.factory.get(reverse("dashboard:admin"))
        request.user = self.admin

        with patch("dashboard.views.render", return_value=HttpResponse()) as mock_render:
            response = admin_dashboard_view(request)

        self.assertEqual(response.status_code, 200)
        context = mock_render.call_args.args[2]
        status_payload = context["chart_status"]
        category_payload = context["chart_category"]

        self.assertIsInstance(status_payload, dict)
        self.assertEqual(status_payload["labels"][0], "Pending")
        self.assertGreaterEqual(status_payload["data"][0], 1)
        self.assertIsInstance(category_payload, dict)
        self.assertIn(self.category.name, category_payload["labels"])
