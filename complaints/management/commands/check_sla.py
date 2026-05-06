from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from complaints.models import ActivityLog, Complaint, Notification
from complaints.services import create_notification, log_activity


ACTIVE_STATUSES = [
    Complaint.Status.PENDING,
    Complaint.Status.UNDER_REVIEW,
    Complaint.Status.RESPONDENT_NOT_CONTACTED,
    Complaint.Status.RESPONDENT_CONTACTED,
    Complaint.Status.WAITING_RESPONDENT_RESPONSE,
    Complaint.Status.RESPONDENT_RESPONSE_RECORDED,
    Complaint.Status.NO_RESPONSE,
    Complaint.Status.FAILED_TO_ATTEND,
    Complaint.Status.SECOND_NOTICE_SENT,
    Complaint.Status.HEARING_SCHEDULED,
    Complaint.Status.IN_MEDIATION,
    Complaint.Status.IN_PROGRESS,
]


class Command(BaseCommand):
    help = "Notify admins and assignees about complaints that passed their SLA deadline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--auto-escalate-days",
            type=int,
            default=0,
            help="If set, mark active overdue complaints as escalated after this many overdue days.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        overdue = Complaint.objects.filter(status__in=ACTIVE_STATUSES, deadline_at__lt=now).select_related(
            "assigned_to", "resident"
        )
        admins = User.objects.filter(Q(role=User.Role.ADMIN) | Q(is_superuser=True)).distinct()
        notified_count = 0
        escalated_count = 0

        for complaint in overdue:
            message = f"Complaint '{complaint.title}' is overdue for SLA response."
            recipients = list(admins)
            if complaint.assigned_to:
                recipients.append(complaint.assigned_to)
            for user in {recipient.id: recipient for recipient in recipients}.values():
                create_notification(
                    user=user,
                    complaint=complaint,
                    message=message,
                    notification_type=Notification.Type.OVERDUE,
                    dedupe=True,
                )
                notified_count += 1
            log_activity(
                complaint=complaint,
                action=ActivityLog.Action.SLA_OVERDUE_FLAGGED,
                target=complaint,
                summary=message,
                metadata={"deadline_at": complaint.deadline_at.isoformat() if complaint.deadline_at else ""},
            )

            auto_escalate_days = options["auto_escalate_days"]
            if auto_escalate_days and (now - complaint.deadline_at).days >= auto_escalate_days:
                complaint.status = Complaint.Status.ESCALATED
                complaint.save(update_fields=["status", "updated_at"])
                escalated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"SLA check complete: {overdue.count()} overdue complaint(s), "
                f"{notified_count} notification(s), {escalated_count} auto-escalation(s)."
            )
        )
