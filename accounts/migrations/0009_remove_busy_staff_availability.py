from django.db import migrations, models


def move_busy_staff_to_available(apps, schema_editor):
    StaffProfile = apps.get_model("accounts", "StaffProfile")
    StaffProfile.objects.filter(availability="BUSY").update(availability="AVAILABLE")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_remove_staffprofile_department"),
    ]

    operations = [
        migrations.RunPython(move_busy_staff_to_available, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="staffprofile",
            name="availability",
            field=models.CharField(
                choices=[
                    ("AVAILABLE", "Available"),
                    ("UNAVAILABLE", "Unavailable"),
                ],
                default="AVAILABLE",
                max_length=20,
            ),
        ),
    ]
