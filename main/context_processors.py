from ohr.settings import TELEPHONE, POCHTA


def notifications(request):
    if request.user.is_authenticated:
        notifications = request.user.notifications.filter(user=request.user, is_read=False)
        notice = request.user.notice.filter(user=request.user, is_read=False)
        return {
            'notifications': notifications,
            'notice': notice,
            'notifications_count': notifications.count() + notice.count()
        }
    return {}


def personal(request):
    return {'telephone':TELEPHONE, 'pochta':POCHTA}