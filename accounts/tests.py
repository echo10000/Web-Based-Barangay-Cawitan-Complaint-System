from django.contrib.auth import get_user
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ResidentProfile, User


class LoginFormTests(TestCase):
    def setUp(self):
        self.password = "StrongPass123"
        self.user = User.objects.create_user(
            username="juan",
            email="juan@example.com",
            password=self.password,
            role=User.Role.RESIDENT,
        )

    def test_user_can_login_with_username(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": self.user.username, "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(get_user(self.client).id, self.user.id)

    def test_user_can_login_with_email(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": self.user.email, "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(get_user(self.client).id, self.user.id)

    def test_user_can_login_with_email_case_insensitively(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "JUAN@EXAMPLE.COM", "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(get_user(self.client).id, self.user.id)

    def test_logout_redirects_to_login_with_feedback(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("accounts:logout"), follow=True)

        self.assertRedirects(response, reverse("accounts:login"))
        self.assertFalse(get_user(self.client).is_authenticated)
        self.assertContains(response, "You have been logged out successfully.")


class AdminAccountActionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="AdminPass123",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.resident = User.objects.create_user(
            username="resident",
            password="ResidentPass123",
            email="resident@example.com",
            role=User.Role.RESIDENT,
        )
        ResidentProfile.objects.create(user=self.resident, phone_number="09170000001", address="Purok 1")

    def test_admin_can_deactivate_and_reactivate_resident(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("accounts:toggle_account_status", kwargs={"pk": self.resident.pk}))
        self.resident.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.resident.is_active)

        self.client.post(reverse("accounts:toggle_account_status", kwargs={"pk": self.resident.pk}))
        self.resident.refresh_from_db()

        self.assertTrue(self.resident.is_active)

    def test_admin_can_edit_resident_account(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("accounts:edit_account", kwargs={"pk": self.resident.pk}),
            {
                "username": "resident_updated",
                "first_name": "Updated",
                "last_name": "Resident",
                "email": "updated@example.com",
                "is_active": "on",
                "phone_number": "09170000002",
                "address": "Purok 2",
                "birth_date": "",
            },
        )
        self.resident.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.resident.username, "resident_updated")
        self.assertEqual(self.resident.email, "updated@example.com")
        self.assertEqual(self.resident.resident_profile.address, "Purok 2")

    def test_non_admin_cannot_toggle_account_status(self):
        self.client.force_login(self.resident)

        response = self.client.post(reverse("accounts:toggle_account_status", kwargs={"pk": self.resident.pk}))
        self.resident.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.resident.is_active)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST_USER="test@example.com",
        DEFAULT_FROM_EMAIL="test@example.com",
    )
    def test_admin_can_email_temporary_password(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("accounts:reset_account_password", kwargs={"pk": self.resident.pk}))
        self.resident.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.resident.check_password("ResidentPass123"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Temporary password:", mail.outbox[0].body)


class ResidentVerificationRequestTests(TestCase):
    def setUp(self):
        self.resident = User.objects.create_user(
            username="resident",
            password="ResidentPass123",
            email="resident@example.com",
            role=User.Role.RESIDENT,
            first_name="Juan",
            last_name="Resident",
        )
        ResidentProfile.objects.create(user=self.resident, phone_number="", address="")

    def test_profile_update_with_required_details_requests_verification(self):
        self.client.force_login(self.resident)
        valid_id = SimpleUploadedFile(
            "valid-id.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )

        response = self.client.post(
            reverse("accounts:profile"),
            {
                "first_name": "Juan",
                "last_name": "Resident",
                "email": "resident@example.com",
                "phone_number": "09170000001",
                "address": "Purok 1-A",
                "purok": "Purok 1-A",
                "household_number": "HH-001",
                "birth_date": "2000-01-02",
                "valid_id_front_image": valid_id,
                "valid_id_back_image": SimpleUploadedFile(
                    "valid-id-back.gif",
                    b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
                    content_type="image/gif",
                ),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.resident.resident_profile.refresh_from_db()
        self.assertEqual(
            self.resident.resident_profile.verification_status,
            ResidentProfile.VerificationStatus.PENDING,
        )
