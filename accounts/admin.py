from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ResidentProfile, StaffProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Barangay Role", {"fields": ("role",)}),)
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")


@admin.register(ResidentProfile)
class ResidentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "address", "created_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "address")


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "position", "phone_number", "created_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "position")
