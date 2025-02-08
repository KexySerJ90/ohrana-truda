import os

from django.contrib.auth import user_logged_in
from django.db.models.signals import post_delete
from django.dispatch import receiver
from user_agents import parse
from main.utils import get_client_ip
from main.models import UploadFiles, UserLoginHistory


@receiver(post_delete, sender=UploadFiles)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """ Уничтожает файл из файловой системы при удалении соответствующего объекта `UploadFiles`. """
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)

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

    reader = Reader('geoip/GeoLite2-City.mmdb')  # путь к базе данных
    response = reader.city(ip)
    city = response.city.name
    country = response.country.iso_code
    return f"{city}, {country}"