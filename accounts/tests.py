import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .forms import ResidentRegistrationForm, ResidentVerificationForm
from .models import ResidentProfile, User


def _test_image(name):
    return SimpleUploadedFile(
        name,
        (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
            b"\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00"
            b"\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02"
            b"\x44\x01\x00\x3b"
        ),
        content_type="image/gif",
    )


class ResidentRegistrationVerificationTests(TestCase):
    def test_registration_requires_valid_id_submission(self):
        form = ResidentRegistrationForm(
            data={
                "username": "resident-no-id",
                "first_name": "Rina",
                "last_name": "Santos",
                "email": "rina@example.com",
                "address": "Purok 1",
                "password1": "StrongerPass123!",
                "password2": "StrongerPass123!",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("valid_id_type", form.errors)
        self.assertIn("valid_id_front_image", form.errors)
        self.assertIn("valid_id_back_image", form.errors)

    def test_registration_saves_valid_id_and_sets_pending_review(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            form = ResidentRegistrationForm(
                data={
                    "username": "resident-with-id",
                    "first_name": "Rina",
                    "last_name": "Santos",
                    "email": "rina@example.com",
                    "address": "Purok 1",
                    "valid_id_type": ResidentProfile.ValidIDType.NATIONAL_ID,
                    "password1": "StrongerPass123!",
                    "password2": "StrongerPass123!",
                },
                files={
                    "valid_id_front_image": _test_image("front.gif"),
                    "valid_id_back_image": _test_image("back.gif"),
                },
            )

            self.assertTrue(form.is_valid(), form.errors)
            user = form.save()
            profile = user.resident_profile
            self.assertEqual(profile.verification_status, ResidentProfile.VerificationStatus.PENDING)
            self.assertTrue(profile.has_valid_id_submission)

    def test_admin_cannot_mark_verified_without_valid_id_submission(self):
        resident = User(username="resident")
        profile = ResidentProfile(user=resident, address="Purok 1")
        form = ResidentVerificationForm(
            data={
                "verify-verification_status": ResidentProfile.VerificationStatus.VERIFIED,
                "verify-verification_notes": "",
            },
            instance=profile,
            prefix="verify",
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Resident cannot be verified", form.non_field_errors()[0])
