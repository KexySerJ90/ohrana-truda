from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone

from main.models import Notice
from users.models import Profile


def send_birthday_notices():
    today = date.today()

    profiles = Profile.objects.filter(date_birth__day=today.day, date_birth__month=today.month)

    for profile in profiles:
        user = profile.user
        notice = Notice(
            user=user,
            message=f"С днём рождения, {user.first_name}!",
            created_at=timezone.now(),
            is_read=False
        )
        notice.save()


scheduler = BackgroundScheduler()
scheduler.add_job(send_birthday_notices, trigger='cron', hour=0)
scheduler.start()