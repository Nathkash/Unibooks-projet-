from .models import Notification


def notifications_non_lues(request):
    if request.user.is_authenticated:
        nb = Notification.objects.filter(
            destinataire=request.user, lue=False
        ).count()
        return {'nb_notifs_non_lues': nb}
    return {'nb_notifs_non_lues': 0}