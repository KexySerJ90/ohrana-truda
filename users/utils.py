from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.mail import send_mail
from functools import wraps
from django import forms
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django_select2.forms import ModelSelect2Widget
from typing import Any
from datetime import timedelta

from study.models import Subject, SubjectCompletion
from users.models import Profession, Notice, SentMessage
import pyotp
COMMON_TEXT_INPUT_ATTRS = {'class': 'form-control'}


class BaseUserView:
    def handle_subjects(self, user):
        sub_titles = None
        if user.status == 'leader':
            sub_titles = ['first_aid', 'safe_method1', 'suot']
        elif user.status == 'medic':
            sub_titles = ['safe_method1']
        elif user.status == 'worker':
            sub_titles = ['first_aid', 'safe_method2']

        if sub_titles:
            subjects = Subject.objects.filter(title__in=sub_titles)
            for sub in subjects:
                subject_completion, created = SubjectCompletion.objects.get_or_create(users=user, subjects=sub)
                user.subject.add(sub)
                subject_completion.save()
        try:
            leader = get_user_model().objects.get(status=get_user_model().Status.LEADER, cat2=user.cat2)
            if leader != user:
                Notice.objects.create(
                    user=leader,
                    message=f"{user.profile.profession} {user.last_name} {user.first_name} завершил регистрацию")
        except ObjectDoesNotExist:
            pass
        Notice.objects.create(
            user=user,
            message=f"Поздравляем, вы завершили регистрацию!"
        )

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


def sent_count(user,purpose):
    thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
    sent_count = SentMessage.objects.filter(user=user, timestamp__gte=thirty_minutes_ago,purpose=purpose).count()
    return sent_count