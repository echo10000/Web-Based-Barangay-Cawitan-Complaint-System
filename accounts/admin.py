from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import PasswordResetOTP, ResidentProfile, StaffProfile, User


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
    list_display = ("user", "position", "availability", "phone_number", "short_responsibilities", "created_at")
    list_filter = ("availability", "specialization_categories")
    search_fields = ("user__username", "user__first_name", "user__last_name", "position", "responsibilities")
    filter_horizontal = ("specialization_categories",)

    @admin.display(description="Staff functions")
    def short_responsibilities(self, obj):
        return (obj.responsibilities[:80] + "...") if len(obj.responsibilities) > 80 else obj.responsibilities


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "otp", "created_at", "is_used")
    list_filter = ("is_used", "created_at")
    search_fields = ("user__username", "user__email", "otp")
    readonly_fields = ("created_at",)
