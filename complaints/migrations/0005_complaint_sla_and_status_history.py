from datetime import timedelta

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


SLA_HOURS = {
    "LOW": 168,
    "NORMAL": 72,
    "HIGH": 48,
    "URGENT": 24,
}


def backfill_deadlines_and_history(apps, schema_editor):
    Complaint = apps.get_model("complaints", "Complaint")
    ComplaintStatusHistory = apps.get_model("complaints", "ComplaintStatusHistory")

    for complaint in Complaint.objects.all().iterator():
        update_fields = []
        if complaint.deadline_at is None:
            complaint.deadline_at = complaint.created_at + timedelta(hours=SLA_HOURS.get(complaint.priority, 72))
            update_fields.append("deadline_at")
        if complaint.status == "RESOLVED" and complaint.resolved_at is None:
            complaint.resolved_at = complaint.updated_at
            update_fields.append("resolved_at")
        if update_fields:
            complaint.save(update_fields=update_fields)
        ComplaintStatusHistory.objects.get_or_create(
            complaint=complaint,
            old_status="",
            new_status=complaint.status,
            defaults={"remarks": "Current status recorded during migration."},
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("complaints", "0004_complaint_priority"),
    ]

    operations = [
        migrations.AddField(
            model_name="complaint",
            name="deadline_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="complaint",
            name="resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="ComplaintStatusHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "old_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PENDING", "Pending"),
                            ("UNDER_REVIEW", "Under Review"),
                            ("IN_PROGRESS", "In Progress"),
                            ("RESOLVED", "Resolved"),
                            ("REJECTED", "Rejected"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "new_status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("UNDER_REVIEW", "Under Review"),
                            ("IN_PROGRESS", "In Progress"),
                            ("RESOLVED", "Resolved"),
                            ("REJECTED", "Rejected"),
                        ],
                        max_length=20,
                    ),
                ),
                ("remarks", models.TextField(blank=True)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "changed_by",
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
                        related_name="status_history",
                        to="complaints.complaint",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Complaint status history",
                "ordering": ["-changed_at"],
            },
        ),
        migrations.RunPython(backfill_deadlines_and_history, migrations.RunPython.noop),
    ]
