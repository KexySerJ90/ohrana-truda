import hashlib
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils import timezone
from django_otp.models import Device
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    class Status(models.TextChoices):
        LEADER=('leader', 'Руководитель')
        MEDIC=('medic', 'Медик')
        WORKER=('worker', 'Рабочий')
        ADMINISTRATION = ('administration', 'Административный персонал')
    email = models.EmailField(_("email address"), unique=True)
    phone=PhoneNumberField(max_length=15, unique=True,null=True, verbose_name='Телефон')
    cat2 = models.ForeignKey('main.Departments', on_delete=models.CASCADE, related_name='cat2', verbose_name="Отделение", null=True)
    subject = models.ManyToManyField('study.Subject', blank=True, related_name='subjs', verbose_name="Предмет")
    status = models.CharField(choices=Status.choices, max_length=100, verbose_name='Статус')
    update = models.DateTimeField(auto_now=True, verbose_name='Время обновления')
    last_activity = models.DateTimeField(default=timezone.now, verbose_name="Последняя авторизация")
    two_factor_enabled = models.BooleanField(default=False, verbose_name='Двухфакторная авторизация')
    reserve_email=models.EmailField(default='',blank=True, null=True, verbose_name='Резервный Email')
    secret_answer = models.CharField(max_length=255, blank=True, null=True, verbose_name='Секретный ответ')
    is_social_user = models.BooleanField(default=False, verbose_name="Социальный юзер?")


    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        constraints = [
            models.UniqueConstraint(fields=['phone'], name='unique_phone', condition=models.Q(phone__isnull=False))
        ]


    def update_last_activity(self):
        self.last_activity = timezone.now()
        self.save()


    def is_online(self):
        return timezone.now() - self.last_activity < timedelta(minutes=5)  # например, 5 минут

    def hashed_id(self) -> str:
        # Хэшируем UUID
        return hashlib.sha256(str(self.pk).encode()).hexdigest()

    def masked_phone(self) -> str|None:
        """Метод для маскирования номера телефона."""
        if self.phone:
            phone_str = str(self.phone)
            return phone_str[:5] + '*'*6 + phone_str[-2:]
        return None

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    patronymic = models.CharField(max_length=100, blank=True, null=True, verbose_name="Отчество (необязательное поле)")
    profession = models.ForeignKey('users.Profession', on_delete=models.CASCADE, verbose_name='Профессия')
    photo = models.ImageField(upload_to="users/%Y/%m/%d/", blank=True, null=True, verbose_name="Фотография")
    date_birth = models.DateField(blank=True, null=True, verbose_name="Дата рождения")
    date_of_work = models.DateField(verbose_name="Дата трудоустройства")
    instructaj = models.BooleanField(default=False, verbose_name="Инструктаж")

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return self.user.username

    def calculate_date(self):
        return 60 - (timezone.now().date() - self.date_of_work).days

class SecurityQuestion(models.Model):
    class SecretQuestions(models.TextChoices):
        PET_NAME = ('pet_name', 'Как зовут Ваше любимое домашнее животное?')
        MOTHER_MAIDEN_NAME = ('mother_maiden_name', 'Какая девичья фамилия у Вашей матери?')
        FIRST_SCHOOL = ('first_school', 'В какой школе Вы учились в первый раз?')
        DREAM_VACATION = ('dream_vacation', 'Какое Ваше самое заветное место для отдыха?')
        FIRST_CAR = ('first_car', 'Какую машину Вы впервые водили?')
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    question = models.CharField(choices=SecretQuestions.choices,max_length=255, verbose_name="Вопрос безопасности")

    def __str__(self):
        return self.user.username


    class Meta:
        verbose_name = "Секретный вопрос"
        verbose_name_plural = "Секретные вопросы"
        ordering = ['-user']

class Profession(models.Model):
    name = models.CharField(max_length=250,verbose_name='Название должности', unique=True, db_index=True)
    equipment = models.ManyToManyField('main.Equipment',blank=True, related_name='siz', verbose_name="Сизы")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Профессия"
        verbose_name_plural = "Профессии"
        ordering = ['-id']
class OTP(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    otp_secret = models.CharField(max_length=40)
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.email
class MailDevice(Device):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')

    def __str__(self):
        try:
            user = self.user
        except ObjectDoesNotExist:
            user = None

        return f'2fa-{user}-{self.timestamp}'


class SentMessage(models.Model):
    class PURPOSE(models.TextChoices):
        RESCUE=('rescue', 'Восстановление пароля')
        RESET=('reset', 'Сброс OTP')
        CONTACT=('contact', 'Контакты')
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    purpose = models.CharField(choices=PURPOSE.choices, max_length=100, verbose_name='Цель')

    class Meta:
        verbose_name = "Количество попыток для отправки сообщений"
        verbose_name_plural = "Количество попыток для отправки сообщений"

    def __str__(self):
        return f'{self.user} - {self.timestamp} -  {dict(SentMessage.PURPOSE.choices)[self.purpose]}'


class Notification(models.Model):
    '''Оповещение по комментариям'''
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, verbose_name='Пользователь',
                             related_name='notifications')
    comment = models.ForeignKey('main.Comment', on_delete=models.CASCADE, verbose_name='Комментарий',
                                related_name='notifications')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')

    class Meta:
        ordering = ['user','-created_at']
        verbose_name = 'Оповещение'
        verbose_name_plural = 'Оповещения'

    def __str__(self):
        return f"{self.user} : {self.comment}, создан {self.created_at.strftime('%d.%m.%Y %H:%M')}"

    def get_absolute_url(self):
        return reverse("main:notification_read", kwargs={"pk": self.pk})

class Notice(models.Model):
    '''Оповещение по событиям'''
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='notice', verbose_name="Пользователь")
    message = models.TextField(verbose_name='Сообщение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')

    class Meta:
        ordering = ['user','-created_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def __str__(self):
        return f"{self.user} : {self.message}, создан {self.created_at.strftime('%d.%m.%Y %H:%M')}"

class UserLoginHistory(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    location = models.CharField(max_length=100, blank=True)  # Для хранения геолокации
    device_type = models.CharField(max_length=50, blank=True)  # Тип устройства (мобильное, десктоп)
    browser = models.CharField(max_length=200, blank=True)  # Браузер
    os = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'История входа пользователей'
        verbose_name_plural = 'История входа пользователей'

    def __str__(self):
        return f"{self.user.username} logged in at {self.login_time.strftime('%d.%m.%Y %H:%M')}"

