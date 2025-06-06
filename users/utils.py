from datetime import timedelta

from django.forms import widgets
from django.utils import timezone
from django.core.mail import send_mail
from functools import wraps
from django import forms
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django_select2.forms import ModelSelect2Widget
from typing import Any
from main.models import SentMessage
from users.models import Profession
import pyotp
COMMON_TEXT_INPUT_ATTRS = {'class': 'form-control'}




def generate_otp() -> tuple:
    """
    Генерирует одноразовый пароль (OTP) и секрет для его использования.

    Возвращает:
    tuple: кортеж из секрета OTP и сгенерированного кода OTP.
    """
    # Генерируем случайный секрет для OTP
    otp_secret = pyotp.random_base32()

    # Создаем объект TOTP с заданным интервалом в 3000 секунд
    otp = pyotp.TOTP(otp_secret, interval=3000)

    # Получаем текущий одноразовый код OTP
    otp_code = otp.now()

    return otp_secret, otp_code

def send_message(message: str, recipient: str, otp_code: str, user) -> None:
    """Представление для отправки сообщений"""
    send_mail(
                    message,
                    f'{message}: {otp_code}',
                    recipient,
                    [user.email],
                    fail_silently=False,
                )
def login_required_redirect(view_func):
    @wraps(view_func)
    def _wrapped_view(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Проверяем, авторизован ли пользователь
        if request.user.is_active:
            # Если авторизован, перенаправляем, например, на главную страницу
            return redirect('main:index')  # замените 'home' на имя вашего URL
        return view_func(request, *args, **kwargs)
    return _wrapped_view


class ProfessionChoiceField(forms.ModelChoiceField):
    """Пользовательское поле для выбора профессии"""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs['queryset'] = Profession.objects.all()
        kwargs['widget'] = ModelSelect2Widget(
            model=Profession,
            search_fields=['name__icontains'],
            attrs=COMMON_TEXT_INPUT_ATTRS,
        )
        super().__init__(*args, **kwargs)


def sent_count(user,purpose):
    thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
    sent_count = SentMessage.objects.filter(user=user, timestamp__gte=thirty_minutes_ago,purpose=purpose).count()
    return sent_count


class CustomEmailWidget(widgets.EmailInput):
    """Пользовательское поле, которое блокирует ввод кириллицы"""
    def __init__(self, attrs=None):
        default_attrs = {'class': 'form-control', 'oninput': "withoutCyr(this)", 'placeholder': 'Введите ваш E-mail'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)