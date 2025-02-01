from django.contrib.auth import user_logged_in, get_user_model
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import SecurityQuestion



@receiver(post_save, sender=get_user_model())
def create_token(sender, instance, created, **kwargs):
    if created:
        refresh_token = RefreshToken.for_user(instance)
        instance.refresh_token = str(refresh_token)
        instance.save()

@receiver(post_delete, sender=SecurityQuestion)
def clear_user_secret_answer(sender, instance, **kwargs):
    # Очищаем поле secret_answer у пользователя при удалении вопроса безопасности
    user = instance.user
    user.secret_answer = None
    user.save()

