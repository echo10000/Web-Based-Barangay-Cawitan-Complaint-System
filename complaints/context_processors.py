from .models import Notification


def resident_notifications(request):
    if not request.user.is_authenticated or not request.user.is_resident:
        return {}

    return {
        "resident_unread_notifications_count": Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).count()
    }
