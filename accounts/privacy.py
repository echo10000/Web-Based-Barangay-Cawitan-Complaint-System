from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.dateparse import parse_date

from complaints.models import ActivityLog
from complaints.services import log_activity
from .models import DataExportRequest


ACCESS_PURPOSES = {
    "CERTIFICATE_ISSUANCE": "Certificate or barangay document issuance",
    "CASE_PROCESSING": "Complaint or case processing",
    "RESIDENT_VERIFICATION": "Resident identity verification",
    "SERVICE_REFERRAL": "Health, social service, or disaster response referral",
    "OFFICIAL_RECORD_UPDATE": "Official resident record update",
}

EXPORT_PURPOSES = {
    "OFFICIAL_MONITORING": "Official complaint monitoring",
    "SLA_REVIEW": "SLA and service performance review",
    "LEGAL_RECORD": "Legal, mediation, or official record preparation",
}

PROHIBITED_PURPOSE_WORDS = {
    "campaign",
    "election",
    "politic",
    "party",
    "vote",
    "voter",
    "buy",
    "ayuda list",
}

SENSITIVE_FILTER_KEYS = {"purok", "assigned_to", "response_status", "mediation_result"}


def is_election_period_restricted():
    today = timezone.localdate()
    raw_windows = getattr(settings, "PRIVACY_ELECTION_RESTRICTION_WINDOWS", "") or ""
    for raw_window in raw_windows.split(","):
        if ":" not in raw_window:
            continue
        start_raw, end_raw = [part.strip() for part in raw_window.split(":", 1)]
        start = parse_date(start_raw)
        end = parse_date(end_raw)
        if start and end and start <= today <= end:
            return True
    return False


def is_valid_access_purpose(value):
    return value in ACCESS_PURPOSES


def clean_filter_dict(querydict):
    return {
        key: value
        for key, value in querydict.items()
        if key not in {"csrfmiddlewaretoken", "page", "export_request", "format"} and value not in ("", None)
    }


def contains_prohibited_purpose(text):
    normalized = (text or "").lower()
    return any(word in normalized for word in PROHIBITED_PURPOSE_WORDS)


def require_resident_access_purpose(request, *, redirect_name="accounts:residents"):
    purpose = request.GET.get("purpose") or request.POST.get("purpose")
    if is_valid_access_purpose(purpose):
        return purpose
    messages.error(request, "Choose an official purpose before viewing resident records.")
    return None


def resident_purpose_redirect_url(base_url, purpose):
    if not purpose:
        return base_url
    return f"{base_url}?{urlencode({'purpose': purpose})}"


def log_resident_directory_access(request, purpose, *, filtered_count, search=""):
    log_activity(
        actor=request.user,
        action=ActivityLog.Action.RESIDENT_DIRECTORY_VIEWED,
        summary="Resident directory viewed for an official purpose.",
        metadata={
            "purpose": purpose,
            "purpose_label": ACCESS_PURPOSES.get(purpose, purpose),
            "filtered_count": filtered_count,
            "searched": bool(search),
            "query": search[:80],
        },
    )


def log_resident_profile_access(request, resident, purpose):
    log_activity(
        actor=request.user,
        action=ActivityLog.Action.RESIDENT_PROFILE_VIEWED,
        target=resident,
        summary=f"Resident profile viewed for {resident.username}.",
        metadata={
            "purpose": purpose,
            "purpose_label": ACCESS_PURPOSES.get(purpose, purpose),
        },
    )


def can_review_export(user, export_request):
    return user.is_authenticated and user.is_privacy_officer and export_request.requested_by_id != user.id


def create_export_request(request, export_type):
    purpose = request.POST.get("export_purpose", "")
    reason = request.POST.get("export_reason", "").strip()
    filters = clean_filter_dict(request.GET)
    if purpose not in EXPORT_PURPOSES:
        messages.error(request, "Choose a valid official export purpose.")
        return None
    if len(reason) < 15:
        messages.error(request, "Enter a specific export reason with at least 15 characters.")
        return None
    if contains_prohibited_purpose(reason) or contains_prohibited_purpose(purpose):
        messages.error(request, "Political, campaign, or vote-related export purposes are prohibited.")
        return None
    if is_election_period_restricted() and any(filters.get(key) for key in SENSITIVE_FILTER_KEYS):
        messages.error(request, "Election-period restrictions block targeted exports by area, staff, or response status.")
        return None

    export_request = DataExportRequest.objects.create(
        export_type=export_type,
        purpose=purpose,
        reason=reason,
        filters=filters,
        requested_by=request.user,
    )
    log_activity(
        actor=request.user,
        action=ActivityLog.Action.DATA_EXPORT_REQUESTED,
        target=export_request,
        summary=f"{export_request.get_export_type_display()} export requested.",
        metadata={"purpose": purpose, "filters": filters},
    )
    return export_request


def require_approved_export_request(request, export_type):
    export_request_id = request.GET.get("export_request")
    if not export_request_id:
        messages.error(request, "Request export approval before downloading report data.")
        return None
    try:
        export_request = DataExportRequest.objects.get(pk=export_request_id, export_type=export_type)
    except DataExportRequest.DoesNotExist:
        messages.error(request, "Export request was not found.")
        return None
    if export_request.status != DataExportRequest.Status.APPROVED:
        messages.error(request, "This export request is not approved for download.")
        return None
    if export_request.requested_by_id != request.user.id:
        messages.error(request, "Only the requester can download an approved export.")
        return None
    current_filters = clean_filter_dict(request.GET)
    current_filters.pop("export_request", None)
    if export_request.filters != current_filters:
        messages.error(request, "Report filters changed after approval. Request a new export approval.")
        return None
    return export_request


def mark_export_used(request, export_request):
    export_request.status = DataExportRequest.Status.USED
    export_request.used_at = timezone.now()
    export_request.save(update_fields=["status", "used_at"])
    log_activity(
        actor=request.user,
        action=ActivityLog.Action.DATA_EXPORTED,
        target=export_request,
        summary=f"{export_request.get_export_type_display()} downloaded.",
        metadata={
            "export_request_id": export_request.pk,
            "purpose": export_request.purpose,
            "filters": export_request.filters,
        },
    )


def redirect_to_reports():
    return redirect("complaints:reports")
