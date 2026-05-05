from django.contrib.auth import get_user
from django.test import TestCase
from django.urls import reverse

from .models import User


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
