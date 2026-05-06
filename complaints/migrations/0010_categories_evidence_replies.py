from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("complaints", "0009_complaint_accuracy_certification_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="complaintcategory",
            name="color",
            field=models.CharField(blank=True, help_text="Optional dashboard color such as #2563eb.", max_length=20),
        ),
        migrations.AddField(
            model_name="complaintcategory",
            name="default_priority",
            field=models.CharField(
                choices=[("LOW", "Low"), ("NORMAL", "Normal"), ("HIGH", "High"), ("URGENT", "Urgent")],
                default="NORMAL",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="complaintcategory",
            name="responsible_department",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="complaintcategory",
            name="target_resolution_hours",
            field=models.PositiveIntegerField(default=72),
        ),
        migrations.AddField(
            model_name="uploadedevidence",
            name="content_type",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="uploadedevidence",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="uploadedevidence",
            name="evidence_type",
            field=models.CharField(
                choices=[
                    ("INITIAL", "Initial Evidence"),
                    ("FOLLOW_UP", "Follow-up Evidence"),
                    ("INSPECTION", "Inspection Photo"),
                    ("RESOLUTION", "Resolution Proof"),
                    ("OTHER", "Other"),
                ],
                default="INITIAL",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="uploadedevidence",
            name="file_size",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="uploadedevidence",
            name="uploaded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="respondentevidence",
            name="content_type",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="respondentevidence",
            name="evidence_type",
            field=models.CharField(
                choices=[
                    ("RESPONDENT", "Respondent Evidence"),
                    ("RESPONSE", "Response Attachment"),
                    ("OTHER", "Other"),
                ],
                default="RESPONDENT",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="respondentevidence",
            name="file_size",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="ComplaintReply",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.TextField()),
                ("attachment", models.FileField(blank=True, null=True, upload_to="complaint_replies/")),
                ("attachment_size", models.PositiveIntegerField(default=0)),
                ("attachment_content_type", models.CharField(blank=True, max_length=100)),
                ("is_public", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "complaint",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="replies",
                        to="complaints.complaint",
                    ),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
