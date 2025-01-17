from django.contrib.auth import user_logged_in
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from rest_framework_simplejwt.tokens import RefreshToken
from user_agents import parse

from main.utils import get_client_ip
from users.models import User, SecurityQuestion, UserLoginHistory


@receiver(post_save, sender=User)
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


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip=get_client_ip(request)
    # Извлечение информации об устройстве
    user_agent = parse(request.META.get('HTTP_USER_AGENT', ''))
    device_type = user_agent.device.family
    os = user_agent.os.family
    browser = user_agent.browser.family

    # Опциональная часть для получения геолокации
    try:
        location = get_location(ip)
    except Exception as e:
        print(f"Error getting geolocation for IP {ip}: {e}")
        location = "Неизвестно"

    UserLoginHistory.objects.create(
        user=user,
        ip_address=ip,
        location=location,
        device_type=device_type,
        browser=browser,
        os=os
    )


def get_location(ip):
    """Функция для получения геолокации по IP"""
    # Здесь можно использовать сторонние сервисы вроде GeoIP
    # Пример использования библиотеки geoip2
    from geoip2.database import Reader

    reader = Reader('geoip/GeoLite2-City.mmdb')  # Замените путь к базе данных
    response = reader.city(ip)
    city = response.city.name
    country = response.country.iso_code
    return f"{city}, {country}"