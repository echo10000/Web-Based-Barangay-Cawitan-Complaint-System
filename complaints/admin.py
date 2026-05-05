from django.contrib import admin

from .models import Complaint, ComplaintCategory, ComplaintResponse, ComplaintStatusHistory, Notification, UploadedEvidence


class UploadedEvidenceInline(admin.TabularInline):
    model = UploadedEvidence
    extra = 0


class ComplaintResponseInline(admin.TabularInline):
    model = ComplaintResponse
    extra = 0
    readonly_fields = ("created_at",)


class ComplaintStatusHistoryInline(admin.TabularInline):
    model = ComplaintStatusHistory
    extra = 0
    readonly_fields = ("old_status", "new_status", "changed_by", "remarks", "changed_at")
    can_delete = False


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("title", "resident", "assigned_to", "category", "priority", "status", "deadline_at", "created_at")
    list_filter = ("priority", "status", "category", "deadline_at", "created_at")
    search_fields = ("title", "description", "resident__username", "resident__first_name", "resident__last_name")
    inlines = [UploadedEvidenceInline, ComplaintResponseInline, ComplaintStatusHistoryInline]


admin.site.register(ComplaintCategory)
admin.site.register(ComplaintResponse)
admin.site.register(ComplaintStatusHistory)
admin.site.register(UploadedEvidence)
admin.site.register(Notification)
