from django.db import migrations, models


def mark_existing_notifications_as_in_app_only(apps, schema_editor):
    Notification = apps.get_model("complaints", "Notification")
    Notification.objects.update(email_status="SKIPPED", sms_status="SKIPPED")


class Migration(migrations.Migration):

    dependencies = [
        ("complaints", "0005_complaint_sla_and_status_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("GENERAL", "General"),
                    ("SUBMITTED", "Complaint Submitted"),
                    ("ASSIGNED", "Complaint Assigned"),
                    ("STATUS_CHANGED", "Status Changed"),
                    ("REMARKS_ADDED", "Remarks Added"),
                    ("OVERDUE", "Overdue"),
                ],
                default="GENERAL",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="link_target",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="notification",
            name="read_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="email_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("SENT", "Sent"),
                    ("FAILED", "Failed"),
                    ("SKIPPED", "Skipped"),
                    ("NOT_CONFIGURED", "Not Configured"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="email_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="email_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="sms_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("SENT", "Sent"),
                    ("FAILED", "Failed"),
                    ("SKIPPED", "Skipped"),
                    ("NOT_CONFIGURED", "Not Configured"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="sms_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="sms_error",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(mark_existing_notifications_as_in_app_only, migrations.RunPython.noop),
    ]
