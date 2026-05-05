from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("complaints", "0003_complaint_contact_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="complaint",
            name="priority",
            field=models.CharField(
                choices=[
                    ("LOW", "Low"),
                    ("NORMAL", "Normal"),
                    ("HIGH", "High"),
                    ("URGENT", "Urgent"),
                ],
                default="NORMAL",
                max_length=20,
            ),
        ),
    ]
