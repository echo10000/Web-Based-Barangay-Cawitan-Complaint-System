from django.db import migrations

CATEGORIES = [
    "Noise Complaint",
    "Garbage and Sanitation",
    "Road and Drainage Issues",
    "Neighbor Dispute",
    "Animal Concern",
    "Safety and Security",
    "Street Lighting",
    "Illegal Parking / Obstruction",
    "Public Property Damage",
    "Others",
]


def seed_categories(apps, schema_editor):
    ComplaintCategory = apps.get_model("complaints", "ComplaintCategory")
    for name in CATEGORIES:
        ComplaintCategory.objects.get_or_create(name=name, defaults={"is_active": True})


def unseed_categories(apps, schema_editor):
    ComplaintCategory = apps.get_model("complaints", "ComplaintCategory")
    ComplaintCategory.objects.filter(name__in=CATEGORIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("complaints", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, reverse_code=unseed_categories),
    ]
