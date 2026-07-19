from chat.models import Message


def global_counts(request):
    unread_notifications_count = 0
    unread_messages_count = 0

    if request.user.is_authenticated:
        unread_notifications_count = request.user.notifications.filter(
            is_read=False
        ).count()

        unread_messages_count = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(
            sender=request.user
        ).distinct().count()

    return {
        'unread_notifications_count': unread_notifications_count,
        'unread_messages_count': unread_messages_count,
    }