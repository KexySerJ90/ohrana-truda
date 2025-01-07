from celery import shared_task

from main.models import Article
from users.models import User
from datetime import date

@shared_task
def create_birthday_articles():
    today = date.today()
    birthday_users = User.objects.filter(date_birth__day=today.day, date_birth__month=today.month)

    for user in birthday_users:
        # Создание статьи для каждого пользователя с днем рождения
        article = Article.objects.create(
            title=f'Happy Birthday, {user.username}!',
            content=f'Congratulations to {user.username} on their birthday today!',
            is_published=True,
        )
        article.save()