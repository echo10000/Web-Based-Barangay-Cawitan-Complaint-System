from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_staffprofile_assignment_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="residentprofile",
            name="household_number",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="residentprofile",
            name="purok",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="residentprofile",
            name="valid_id_image",
            field=models.ImageField(blank=True, null=True, upload_to="resident_ids/"),
        ),
        migrations.AddField(
            model_name="residentprofile",
            name="verification_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="residentprofile",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("UNVERIFIED", "Unverified"),
                    ("PENDING", "Pending Verification"),
                    ("VERIFIED", "Verified"),
                    ("REJECTED", "Rejected"),
                ],
                default="UNVERIFIED",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="residentprofile",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="residentprofile",
            name="verified_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="verified_residents",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="passwordresetotp",
            name="failed_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="passwordresetotp",
            name="last_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="passwordresetotp",
            name="otp_hash",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="passwordresetotp",
            name="resend_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
