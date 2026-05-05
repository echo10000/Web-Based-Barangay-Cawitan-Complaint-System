import json
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import User
from .models import Complaint, Notification


ACTIVE_ASSIGNMENT_STATUSES = [
    Complaint.Status.PENDING,
    Complaint.Status.UNDER_REVIEW,
    Complaint.Status.IN_PROGRESS,
]


def get_staff_assignment_options(complaint, limit=8, include_unavailable=True):
    staff_members = (
        User.objects.filter(role=User.Role.STAFF, is_active=True)
        .select_related("staff_profile")
        .prefetch_related("staff_profile__specialization_categories")
        .annotate(
            active_workload=Count(
                "assigned_complaints",
                filter=Q(assigned_complaints__status__in=ACTIVE_ASSIGNMENT_STATUSES),
            ),
            overdue_workload=Count(
                "assigned_complaints",
                filter=Q(
                    assigned_complaints__status__in=ACTIVE_ASSIGNMENT_STATUSES,
                    assigned_complaints__deadline_at__lt=timezone.now(),
                ),
            ),
        )
    )
    options = []
    for staff in staff_members:
        try:
            profile = staff.staff_profile
            availability = profile.availability
            availability_label = profile.get_availability_display()
            specializations = list(profile.specialization_categories.all())
            specialization_match = bool(complaint.category and complaint.category in specializations)
            team = profile.department or profile.position or "No team set"
        except Exception:
            availability = ""
            availability_label = "No availability set"
            specialization_match = False
            team = "No team set"

        if availability == "UNAVAILABLE" and not include_unavailable:
            continue

        availability_rank = {
            "AVAILABLE": 0,
            "BUSY": 1,
            "UNAVAILABLE": 2,
        }.get(availability, 3)
        score = availability_rank * 100 + staff.active_workload * 10 + staff.overdue_workload
        if specialization_match:
            score -= 20

        options.append(
            {
                "user": staff,
                "team": team,
                "availability": availability_label,
                "active_workload": staff.active_workload,
                "overdue_workload": staff.overdue_workload,
                "specialization_match": specialization_match,
                "score": score,
            }
        )
    return sorted(options, key=lambda item: (item["score"], item["user"].last_name, item["user"].first_name))[:limit]


def choose_auto_assignee(complaint):
    options = get_staff_assignment_options(complaint, limit=1, include_unavailable=False)
    return options[0]["user"] if options else None


def get_user_phone_number(user):
    for attr in ("resident_profile", "staff_profile"):
        try:
            profile = getattr(user, attr)
        except Exception:
            profile = None
        phone_number = getattr(profile, "phone_number", "")
        if phone_number:
            return phone_number
    return ""


def create_notification(
    *,
    user,
    complaint=None,
    message,
    notification_type=Notification.Type.GENERAL,
    link_target="",
    send_email=True,
    send_sms=True,
    dedupe=False,
):
    if not link_target and complaint:
        link_target = complaint.get_absolute_url()
    defaults = {
        "notification_type": notification_type,
        "link_target": link_target,
    }
    if dedupe:
        notification, created = Notification.objects.get_or_create(
            user=user,
            complaint=complaint,
            message=message,
            defaults=defaults,
        )
        if not created:
            return notification
    else:
        notification = Notification.objects.create(
            user=user,
            complaint=complaint,
            message=message,
            **defaults,
        )

    deliver_notification(notification, send_email=send_email, send_sms=send_sms)
    return notification


def deliver_notification(notification, *, send_email=True, send_sms=True):
    update_fields = []
    if send_email:
        deliver_notification_email(notification, update_fields)
    else:
        notification.email_status = Notification.DeliveryStatus.SKIPPED
        update_fields.append("email_status")

    if send_sms:
        deliver_notification_sms(notification, update_fields)
    else:
        notification.sms_status = Notification.DeliveryStatus.SKIPPED
        update_fields.append("sms_status")

    if update_fields:
        notification.save(update_fields=update_fields)


def deliver_notification_email(notification, update_fields):
    user = notification.user
    if not user.email:
        notification.email_status = Notification.DeliveryStatus.SKIPPED
        update_fields.append("email_status")
        return

    if not settings.EMAIL_HOST_USER:
        notification.email_status = Notification.DeliveryStatus.NOT_CONFIGURED
        notification.email_error = "EMAIL_HOST_USER is not configured."
        update_fields.extend(["email_status", "email_error"])
        return

    try:
        send_mail(
            "Barangay Cawitan Complaint Update",
            notification.message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception as exc:
        notification.email_status = Notification.DeliveryStatus.FAILED
        notification.email_error = str(exc)
        update_fields.extend(["email_status", "email_error"])
    else:
        notification.email_status = Notification.DeliveryStatus.SENT
        notification.email_sent_at = timezone.now()
        notification.email_error = ""
        update_fields.extend(["email_status", "email_sent_at", "email_error"])


def deliver_notification_sms(notification, update_fields):
    phone_number = get_user_phone_number(notification.user)
    if not phone_number:
        notification.sms_status = Notification.DeliveryStatus.SKIPPED
        update_fields.append("sms_status")
        return

    sms_webhook_url = getattr(settings, "SMS_WEBHOOK_URL", "")
    if not sms_webhook_url:
        notification.sms_status = Notification.DeliveryStatus.NOT_CONFIGURED
        notification.sms_error = "SMS_WEBHOOK_URL is not configured."
        update_fields.extend(["sms_status", "sms_error"])
        return

    payload = json.dumps(
        {
            "to": phone_number,
            "message": notification.message,
            "notification_id": notification.id,
        }
    ).encode("utf-8")
    sms_request = urlrequest.Request(
        sms_webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(sms_request, timeout=10) as response:
            if response.status >= 400:
                raise HTTPError(sms_webhook_url, response.status, response.reason, response.headers, None)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        notification.sms_status = Notification.DeliveryStatus.FAILED
        notification.sms_error = str(exc)
        update_fields.extend(["sms_status", "sms_error"])
    else:
        notification.sms_status = Notification.DeliveryStatus.SENT
        notification.sms_sent_at = timezone.now()
        notification.sms_error = ""
        update_fields.extend(["sms_status", "sms_sent_at", "sms_error"])
