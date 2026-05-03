from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("complaints", "0002_seed_categories"),
    ]

    operations = [
        migrations.AddField(
            model_name="complaint",
            name="contact_number",
            field=models.CharField(blank=True, max_length=20, verbose_name="Contact Number"),
        ),
    ]
