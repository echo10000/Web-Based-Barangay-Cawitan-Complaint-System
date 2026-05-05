from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("complaints", "0005_complaint_sla_and_status_history"),
        ("accounts", "0003_passwordresetotp"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffprofile",
            name="availability",
            field=models.CharField(
                choices=[
                    ("AVAILABLE", "Available"),
                    ("BUSY", "Busy"),
                    ("UNAVAILABLE", "Unavailable"),
                ],
                default="AVAILABLE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="staffprofile",
            name="department",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="staffprofile",
            name="specialization_categories",
            field=models.ManyToManyField(
                blank=True,
                related_name="specialized_staff_profiles",
                to="complaints.complaintcategory",
            ),
        ),
    ]
