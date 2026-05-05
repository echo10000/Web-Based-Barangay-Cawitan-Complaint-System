from django.db import migrations, models


DEFAULT_STAFF_RESPONSIBILITIES = "\n".join(
    [
        "Receive and review complaints",
        "Categorize complaints by type and urgency",
        "Assign or forward complaints to the correct handler",
        "Update complaint status and internal notes",
        "Communicate updates to complainants",
        "Upload evidence, inspection notes, or resolution proof",
        "Monitor overdue and urgent complaints",
        "Prepare complaint summaries and reports",
    ]
)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffprofile",
            name="responsibilities",
            field=models.TextField(blank=True, default=DEFAULT_STAFF_RESPONSIBILITIES),
        ),
    ]
