from .models import Notification


def resident_notifications(request):
    if not request.user.is_authenticated:
        return {}

    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False,
    ).count()
    return {
        "unread_notifications_count": unread_count,
        "resident_unread_notifications_count": unread_count,
    }
