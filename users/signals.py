from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from rest_framework_simplejwt.tokens import RefreshToken

from study.models import Achievement
from users.models import SecurityQuestion, Profile


@receiver(post_save, sender=get_user_model())
def create_token(sender, instance, created, **kwargs):
    if created:
        refresh_token = RefreshToken.for_user(instance)
        instance.refresh_token = str(refresh_token)
        Achievement.objects.create(user=instance, type='site_entry')
        instance.save()

@receiver(post_delete, sender=SecurityQuestion)
def clear_user_secret_answer(sender, instance, **kwargs):
    # Очищаем поле secret_answer у пользователя при удалении вопроса безопасности
    user = instance.user
    user.secret_answer = None
    user.save()


@receiver(post_save, sender=Profile)
def create_photo_achievement(sender, instance, created, update_fields, **kwargs):
    """
    Функция-обработчик сигнала post_save для модели Profile.
    Проверяет изменение поля photo и создает достижение 'full_profile'.
    """
    if update_fields is None or 'photo' in update_fields:
        if instance.photo:
            Achievement.objects.get_or_create(user=instance.user, type='photo_profile')