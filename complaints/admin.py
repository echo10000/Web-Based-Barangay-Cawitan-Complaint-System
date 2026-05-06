from django.contrib import admin

from .models import (
    Complaint,
    ComplaintCategory,
    ComplaintResponse,
    ComplaintStatusHistory,
    Escalation,
    HearingMediation,
    Notification,
    Respondent,
    RespondentEvidence,
    UploadedEvidence,
)


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


class RespondentEvidenceInline(admin.TabularInline):
    model = RespondentEvidence
    extra = 0


class HearingMediationInline(admin.TabularInline):
    model = HearingMediation
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "resident",
        "assigned_to",
        "category",
        "priority",
        "status",
        "privacy_consent",
        "consented_at",
        "deadline_at",
        "created_at",
    )
    list_filter = ("priority", "status", "privacy_consent", "category", "deadline_at", "created_at")
    search_fields = ("title", "description", "resident__username", "resident__first_name", "resident__last_name")
    inlines = [
        UploadedEvidenceInline,
        RespondentEvidenceInline,
        HearingMediationInline,
        ComplaintResponseInline,
        ComplaintStatusHistoryInline,
    ]


admin.site.register(ComplaintCategory)
admin.site.register(ComplaintResponse)
admin.site.register(ComplaintStatusHistory)
admin.site.register(Respondent)
admin.site.register(RespondentEvidence)
admin.site.register(HearingMediation)
admin.site.register(Escalation)
admin.site.register(UploadedEvidence)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "notification_type",
        "complaint",
        "is_read",
        "email_status",
        "created_at",
    )
    list_filter = ("notification_type", "is_read", "email_status", "created_at")
    search_fields = ("user__username", "user__email", "message", "complaint__title")
    readonly_fields = ("created_at", "read_at", "email_sent_at")
