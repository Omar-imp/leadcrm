from .models import EcommerceNotification


def ecommerce_notifications(request):
    if not request.user.is_authenticated:
        return {}
    count = EcommerceNotification.objects.filter(user=request.user, is_read=False).count()
    return {'unread_notif_count': count}
