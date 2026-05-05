from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import ResidentProfile, StaffProfile
from datetime import date

User = get_user_model()


class Command(BaseCommand):
    help = "Create sample accounts for all user roles (Admin, Staff, Resident)"

    def handle(self, *args, **options):
        # Admin Account
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@barangay.gov",
                "first_name": "System",
                "last_name": "Administrator",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("Admin123!")
            admin.save()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Created Admin account - Username: admin | Password: Admin123!")
            )
        else:
            self.stdout.write(self.style.WARNING("✓ Admin account already exists"))

        # Staff Accounts
        staff_accounts = [
            {
                "username": "staff_maria",
                "email": "maria.santos@barangay.gov",
                "first_name": "Maria",
                "last_name": "Santos",
                "position": "Complaints Coordinator",
                "password": "Staff123!",
            },
            {
                "username": "staff_juan",
                "email": "juan.dela.cruz@barangay.gov",
                "first_name": "Juan",
                "last_name": "Dela Cruz",
                "position": "Barangay Councilor",
                "password": "Staff123!",
            },
            {
                "username": "staff_rosa",
                "email": "rosa.reyes@barangay.gov",
                "first_name": "Rosa",
                "last_name": "Reyes",
                "position": "Administrative Officer",
                "password": "Staff123!",
            },
        ]

        for staff_data in staff_accounts:
            password = staff_data.pop("password")
            position = staff_data.pop("position")
            staff_user, created = User.objects.get_or_create(
                username=staff_data["username"],
                defaults={
                    **staff_data,
                    "role": User.Role.STAFF,
                    "is_staff": True,
                },
            )
            if created:
                staff_user.set_password(password)
                staff_user.save()
                StaffProfile.objects.get_or_create(
                    user=staff_user,
                    defaults={
                        "position": position,
                        "phone_number": "+63 9XX-XXX-XXXX",
                    },
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Created Staff account - Username: {staff_data['username']} | Password: {password}"
                    )
                )
            else:
                self.stdout.write(self.style.WARNING(f"✓ Staff account {staff_data['username']} already exists"))

        # Resident Accounts
        resident_accounts = [
            {
                "username": "resident_ana",
                "email": "ana.villareal@email.com",
                "first_name": "Ana",
                "last_name": "Villareal",
                "address": "123 Main Street, Cawitan",
                "phone_number": "09171234567",
                "password": "Resident123!",
            },
            {
                "username": "resident_pedro",
                "email": "pedro.garcia@email.com",
                "first_name": "Pedro",
                "last_name": "Garcia",
                "address": "456 Oak Avenue, Cawitan",
                "phone_number": "09175678901",
                "password": "Resident123!",
            },
            {
                "username": "resident_lucia",
                "email": "lucia.bautista@email.com",
                "first_name": "Lucia",
                "last_name": "Bautista",
                "address": "789 Maple Drive, Cawitan",
                "phone_number": "09179876543",
                "password": "Resident123!",
            },
            {
                "username": "resident_carlos",
                "email": "carlos.moreno@email.com",
                "first_name": "Carlos",
                "last_name": "Moreno",
                "address": "321 Pine Street, Cawitan",
                "phone_number": "09175554321",
                "password": "Resident123!",
            },
        ]

        for resident_data in resident_accounts:
            password = resident_data.pop("password")
            phone_number = resident_data.pop("phone_number")
            address = resident_data.pop("address")
            resident_user, created = User.objects.get_or_create(
                username=resident_data["username"],
                defaults={
                    **resident_data,
                    "role": User.Role.RESIDENT,
                },
            )
            if created:
                resident_user.set_password(password)
                resident_user.save()
                ResidentProfile.objects.get_or_create(
                    user=resident_user,
                    defaults={
                        "phone_number": phone_number,
                        "address": address,
                        "birth_date": date(1985, 1, 15),
                    },
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Created Resident account - Username: {resident_data['username']} | Password: {password}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"✓ Resident account {resident_data['username']} already exists")
                )

        self.stdout.write(self.style.SUCCESS("\n✓ Sample accounts creation completed!"))
