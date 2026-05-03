from django.contrib import admin

from .models import Complaint, ComplaintCategory, ComplaintResponse, Notification, UploadedEvidence


class UploadedEvidenceInline(admin.TabularInline):
    model = UploadedEvidence
    extra = 0


class ComplaintResponseInline(admin.TabularInline):
    model = ComplaintResponse
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("title", "resident", "assigned_to", "category", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("title", "description", "resident__username", "resident__first_name", "resident__last_name")
    inlines = [UploadedEvidenceInline, ComplaintResponseInline]


admin.site.register(ComplaintCategory)
admin.site.register(ComplaintResponse)
admin.site.register(UploadedEvidence)
admin.site.register(Notification)
