import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from functools import wraps
from django import forms
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django_select2.forms import ModelSelect2Widget
from typing import Any
from users.models import User, Profession
import pyotp
COMMON_TEXT_INPUT_ATTRS = {'class': 'form-control'}


class UserQuerysetMixin:
    """
    Миксин для получения queryset пользователей в зависимости от их статуса.
    """

    def get_user_queryset(self, user):
        """
        Возвращает queryset активных пользователей, если у пользователя есть соответствующие права доступа.

        Параметры:
        user (User): объект пользователя, для которого необходимо получить queryset.

        Возвращает:
        QuerySet: queryset активных пользователей, отфильтрованный по категории и отсортированный по статусу.

        """
        # Проверяем статус пользователя и его права
        if user.status == User.Status.LEADER or user.is_superuser or user.is_staff:
            # Получаем активных пользователей с той же категорией и предзагружаем связанные данные
            return User.objects.filter(
                cat2=user.cat2,
                is_active=True
            ).prefetch_related('subject_completions__subjects').order_by('status')

        # Если у пользователя нет прав доступа, выбрасываем исключение
        raise PermissionDenied("You do not have permission to access this resource.")


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
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs['queryset'] = Profession.objects.all()
        kwargs['widget'] = ModelSelect2Widget(
            model=Profession,
            search_fields=['name__icontains'],
            attrs=COMMON_TEXT_INPUT_ATTRS,
        )
        super().__init__(*args, **kwargs)


