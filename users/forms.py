import datetime
import re
from django.contrib.auth.forms import  _unicode_ci_compare
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Q
from django.core.exceptions import ValidationError
from bootstrap_datepicker_plus.widgets import DatePickerInput
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm, PasswordResetForm
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_recaptcha.fields import ReCaptchaField
from main.utils import Leap_years
from users.models import User, Profession, SecurityQuestion, Profile, Departments
from django_select2.forms import ModelSelect2Widget
from phonenumber_field.formfields import PhoneNumberField

from users.utils import COMMON_TEXT_INPUT_ATTRS, ProfessionChoiceField, CustomEmailWidget


# Определим общий стиль для текстовых полей


class LoginUserForm(AuthenticationForm):
    username = forms.CharField(label="Логин, E-mail или телефон",
                               widget=forms.TextInput({**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите Логин, E-mail или телефон'}))
    password = forms.CharField(label="Пароль",
                               widget=forms.PasswordInput({'oncopy': 'return false;',**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите пароль'}))
    remember_me = forms.BooleanField(label="Запомни меня", required=False,
                                     widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    # recaptcha = ReCaptchaField(label='')

    class Meta:
        model = get_user_model()
        fields = ['username', 'password', 'remember_me']
        # fields = ['username', 'password', 'recaptcha', 'remember_me']


class OTPForm(forms.Form):
    otp = forms.CharField(label='Введите одноразовый пароль', min_length=6, max_length=6, required=True,
                          widget=forms.NumberInput(attrs=COMMON_TEXT_INPUT_ATTRS))


class RegisterUserForm(UserCreationForm):
    STATUS_CHOICES = [('', 'Выберите статус')] + User.Status.choices
    SEX_CHOICES = [('', 'Выберите пол')] + Profile.Sex.choices
    email = forms.EmailField(widget=CustomEmailWidget())
    status = forms.ChoiceField(choices=STATUS_CHOICES, label='Статус',
                               widget=forms.Select(attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Выберите статус'}))
    username = forms.CharField(label="Логин", widget=forms.TextInput(
        attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите логин'}))
    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput(
        attrs={'oncopy': 'return false;',**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите пароль'}))
    password2 = forms.CharField(label="Повтор пароля", widget=forms.PasswordInput(
        attrs={'oncopy': 'return false;',**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Повторите пароль'}))
    date_of_work = forms.DateField(label='Дата Трудоустройства', widget=DatePickerInput(options={
        "format": "DD/MM/YYYY",
        "minDate": (datetime.datetime.now() - datetime.timedelta(days=60 * 365 + Leap_years())),
        "maxDate": (datetime.datetime.now()),
        "locale": "ru",
    }))
    phone = PhoneNumberField(label="Телефон (необязательное поле)", required=False, widget=forms.TextInput(
        {**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите номер телефона в формате +79999999999'}))
    cat2 = forms.ModelChoiceField(
        label="Отделение",
        empty_label='Выберите отделение',
        queryset=Departments.objects.exclude(id__in=(1, 2)),  # исключаем категорию с id=1
        # queryset=Departments.objects.all(),
        widget=ModelSelect2Widget(
            model=Departments,
            search_fields=['name__icontains'],
            attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Выберите отделение'},
        ))
    profession = ProfessionChoiceField(label="Профессия", empty_label='Выберите профессию', widget=forms.Select(
        attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Выберите профессию'}))
    sex=forms.ChoiceField(choices=SEX_CHOICES, label="Пол", widget=forms.Select(
        attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Выберите пол'}))
    patronymic=forms.CharField(label='Отчество', required=False, widget=forms.TextInput(attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите отчество'}))

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'phone', 'last_name', 'first_name', 'patronymic', 'sex','cat2', 'status', 'profession',
                  'date_of_work', 'password1', 'password2']
        labels = {
            'email': 'E-mail',
            'first_name': "Имя",
            'last_name': "Фамилия",
        }
        widgets = {
            'email': forms.TextInput(attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите ваш E-mail'}),
            'first_name': forms.TextInput(attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите имя'}),
            'last_name': forms.TextInput(attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите фамилию'}),
        }

    def save(self, commit=True):
        user_data = {field: self.cleaned_data[field] for field in self.Meta.fields if
                     field not in ['patronymic', 'profession', 'date_of_work', 'sex', 'password1','password2']}
        # Сохраняем пользователя
        user = get_user_model()(**user_data)
        user.set_password(self.cleaned_data['password1'])# Устанавливаем пароль
        if commit and hasattr(self, "save_m2m"):
            # user.save()
            self.save_m2m()

        return user

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        cat2 = cleaned_data.get('cat2')

        # Проверка на уникальность статуса LEADER в ее отделении
        if status == User.Status.LEADER and cat2 is not None:
            if User.objects.filter(cat2=cat2, status=User.Status.LEADER).exists():
                raise ValidationError("В Вашем подразделении уже есть руководитель.")
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_model().objects.filter(Q(reserve_email=email) | Q(email=email)).exists():
            raise forms.ValidationError("Пользователь с таким E-mail уже существует!")
        return email

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if phone:
            if get_user_model().objects.filter(phone=phone).exists():
                raise forms.ValidationError("Пользователь с таким Телефоном уже существует!")
        return phone

    def clean_date_of_work(self):
        date_of_work = self.cleaned_data.get('date_of_work')
        if date_of_work and date_of_work > datetime.date.today():
            raise forms.ValidationError("Выбранная дата не может быть позже сегодняшней даты.")
        return date_of_work


class CustomClearableFileInput(forms.ClearableFileInput):
    clear_checkbox_label = "Убрать фото"
    input_text = "Изменить фото"
    checked = False
    template_name = 'users/includes/custom_clearable_file_input.html'


class ProfileUserForm(forms.ModelForm):
    SEX_CHOICES = [('', 'Выберите пол')] + Profile.Sex.choices
    username = forms.CharField(disabled=True, label='Логин', widget=forms.TextInput(attrs=COMMON_TEXT_INPUT_ATTRS))
    masked_phone = forms.CharField(label="Телефон", required=False, disabled=True,
                                   widget=forms.TextInput(attrs=COMMON_TEXT_INPUT_ATTRS))
    photo = forms.ImageField(label='Фото', required=False, widget=CustomClearableFileInput())
    # this_year = datetime.date.today().year
    # date_birth = forms.DateField(label='Дата Рождения',widget=forms.SelectDateWidget(years=tuple(range(this_year-100, this_year-16)),
    #                                                                                  ))
    date_birth = forms.DateField(label='Дата Рождения', required=False, widget=DatePickerInput(options={
        "format": "DD/MM/YYYY",
        "maxDate": (datetime.datetime.now() - datetime.timedelta(days=16 * 365 + Leap_years())),
        "locale": "ru",
    }))
    profession = ProfessionChoiceField(label="Профессия", empty_label='Выберите профессию')
    patronymic=forms.CharField(label='Отчество', required=False, widget=forms.TextInput(attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите отчество'}))
    sex = forms.ChoiceField(choices=SEX_CHOICES, label="Пол", widget=forms.Select(
        attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Выберите пол'}))

    class Meta:
        model = get_user_model()
        fields = ['photo', 'username', 'last_name', 'first_name', 'patronymic', 'sex', 'masked_phone', 'cat2', 'status',
                  'profession', 'date_birth']
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
        }
        widgets = {
            'first_name': forms.TextInput(
                attrs={**COMMON_TEXT_INPUT_ATTRS, 'required': 'true', 'placeholder': 'Введите имя'}),
            'last_name': forms.TextInput(
                attrs={**COMMON_TEXT_INPUT_ATTRS, 'required': 'true', 'placeholder': 'Введите фамилию'}),
            'profession': forms.TextInput(attrs=COMMON_TEXT_INPUT_ATTRS),
            'status': forms.Select(attrs=COMMON_TEXT_INPUT_ATTRS),
            'cat2': forms.Select(attrs=COMMON_TEXT_INPUT_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cat2'].disabled = True
        self.fields['status'].disabled = True
        if self.instance and self.instance.phone:  # Проверяем наличие номера телефона
            self.fields['masked_phone'].initial = self.instance.masked_phone()
        else:
            del self.fields['masked_phone']  # предотвращает изменение на клиентской стороне

    def save(self, commit=True):
        user=get_user_model().objects.get(username=self.cleaned_data['username'])
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={'date_of_work': datetime.date.today(), 'profession':Profession.objects.get(id=1)})
        for field in self.Meta.fields:
            if field == 'photo':
                # Если поле photo не пустое, устанавливаем новое значение
                if self.cleaned_data['photo']:
                    setattr(profile, field, self.cleaned_data[field])
                # Иначе удаляем текущую фотографию
                else:
                    profile.photo.delete(save=False)
            elif field not in ['username', 'patronymic', 'profession', 'date_birth', 'date_of_work','masked_phone']:
                setattr(user, field, self.cleaned_data[field])
            elif field in ['patronymic', 'profession', 'sex', 'date_birth','date_of_work']:
                setattr(profile, field, self.cleaned_data[field])
        if commit:
            user.save()
            profile.save()
            self._save_m2m()
        else:
            self.save_m2m = self._save_m2m
        return self.instance

    def clean_name_field(self, field_name, error_message):
        value = self.cleaned_data.get(field_name)
        if value and not re.match(r'^[А-Яа-яЁёA-Za-z\-]+$', value):  # уберите лишние обратные слеши
            raise ValidationError(error_message)
        return value

    def clean_first_name(self):
        return self.clean_name_field('first_name', 'Имя должно содержать только буквы или дефис.')

    def clean_last_name(self):
        return self.clean_name_field('last_name', 'Фамилия должна содержать только буквы или дефис.')

    def clean_patronymic(self):
        return self.clean_name_field('patronymic', 'Отчество должно содержать только буквы или дефис.')

    def clean_cat2(self):
        cat2 = self.cleaned_data.get('cat2')
        if cat2 and self.instance and self.instance.pk:
            user = self.instance  # текущий пользователь профиля
            if user.is_staff:  # проверка, что пользователь является администратором
                return cat2  # возвращает значение, если пользователь является администратором
            else:
                if cat2 != self.instance.cat2:
                    raise forms.ValidationError(
                        "Вы не можете изменить это поле.")  # вызов ошибки, если пользователь не является администратором
        return cat2

    def clean_status(self):
        # Проверка на сервере для предотвращения изменения status
        status = self.cleaned_data.get('status')
        if status and self.instance and self.instance.pk:
            if status != self.instance.status:
                raise forms.ValidationError("Вы не можете изменить это поле.")
        return status

    def clean_date_birth(self):
        date_birth = self.cleaned_data.get('date_birth')
        if date_birth:
            today = datetime.date.today()
            age = today.year - date_birth.year - ((today.month, today.day) < (date_birth.month, date_birth.day))
            if age < 16:
                raise ValidationError("Вы должны быть старше 16 лет.")
        return date_birth

    def clean_phone(self):
        phone = self.cleaned_data.get('phone') or self.instance.phone
        if phone:
            if get_user_model().objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Такой Телефон уже существует!")
        return phone


class WelcomeSocialForm(ProfileUserForm):
    email = None
    photo = None
    date_birth = None
    STATUS_CHOICES = [('', 'Выберите статус')] + User.Status.choices
    status = forms.ChoiceField(choices=STATUS_CHOICES, label='Статус',
                               widget=forms.Select(attrs=COMMON_TEXT_INPUT_ATTRS))
    cat2 = forms.ModelChoiceField(
        label="Отделение",
        empty_label='Выберите отделение',
        queryset=Departments.objects.exclude(id__in=(1, 2)),  # исключаем категорию с id=1
        widget=ModelSelect2Widget(
            model=Departments,
            search_fields=['name__icontains'],
            attrs=COMMON_TEXT_INPUT_ATTRS,
        ))
    date_of_work = forms.DateField(label='Дата Трудоустройства', widget=DatePickerInput(options={
        "format": "DD/MM/YYYY",
        "minDate": (datetime.datetime.now() - datetime.timedelta(days=60 * 365 + Leap_years())),
        "maxDate": (datetime.datetime.now()),
        "locale": "ru",
    }))

    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'patronymic', 'cat2', 'status',
                  'profession', 'date_of_work']

        widgets = {
            'first_name': forms.TextInput(attrs={**COMMON_TEXT_INPUT_ATTRS, 'required': 'true','placeholder': 'Введите имя'}),
            'last_name': forms.TextInput(attrs={**COMMON_TEXT_INPUT_ATTRS, 'required': 'true','placeholder': 'Введите фамилию'}),
            'profession': forms.TextInput(attrs=COMMON_TEXT_INPUT_ATTRS),
            'status': forms.Select(attrs=COMMON_TEXT_INPUT_ATTRS),
            'cat2': forms.Select(attrs=COMMON_TEXT_INPUT_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cat2'].disabled = False
        self.fields['status'].disabled = False

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        cat2 = cleaned_data.get('cat2')

        # Проверка на уникальность статуса LEADER в ее отделении
        if status == User.Status.LEADER and cat2 is not None:
            if User.objects.filter(cat2=cat2, status=User.Status.LEADER).exists():
                raise ValidationError("В Вашем подразделении уже есть руководитель.")
        return cleaned_data


    def clean_date_of_work(self):
        date_of_work = self.cleaned_data.get('date_of_work')
        if date_of_work and date_of_work > datetime.date.today():
            raise forms.ValidationError("Выбранная дата не может быть позже сегодняшней даты.")
        return date_of_work

    '''Переопределяю методы clean_cat2 и clean_status, чтобы не было ошибки'''

    def clean_cat2(self):
        return self.cleaned_data.get('cat2')

    def clean_status(self):
        return self.cleaned_data.get('status')


class UserForgotPasswordForm(PasswordResetForm):
    email = forms.EmailField(
        widget=CustomEmailWidget()
    )
    def get_users(self, email):
        email_field_name = get_user_model().get_email_field_name()
        # Фильтруем пользователей по основному email и reserve_email
        active_users = get_user_model()._default_manager.filter(
            Q(**{f"{email_field_name}__iexact": email}) | Q(reserve_email__iexact=email),
            is_active=True,
        )

        return (
            u
            for u in active_users
            if u.has_usable_password()
               and _unicode_ci_compare(email, getattr(u, email_field_name)) or _unicode_ci_compare(email,                                                                                               u.reserve_email)
        )
    def save(
            self,
            domain_override=None,
            subject_template_name="registration/password_reset_subject.txt",
            email_template_name="registration/password_reset_email.html",
            use_https=False,
            token_generator=default_token_generator,
            from_email=None,
            request=None,
            html_email_template_name=None,
            extra_email_context=None,
    ):
        email = self.cleaned_data["email"]
        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override
        email_field_name = get_user_model().get_email_field_name()
        for user in self.get_users(email):
            if user.reserve_email and email==user.reserve_email:
                user_email = getattr(user, 'reserve_email')
            else:
                user_email = getattr(user, email_field_name)
            context = {
                "email": user_email,
                "domain": domain,
                "site_name": site_name,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "user": user,
                "token": token_generator.make_token(user),
                "protocol": "https" if use_https else "http",
                **(extra_email_context or {}),
            }
            self.send_mail(
                subject_template_name,
                email_template_name,
                context,
                from_email,
                user_email,
                html_email_template_name=html_email_template_name,
            )


    def clean_email(self):
        email = self.cleaned_data['email']
        if not get_user_model().objects.filter(Q(reserve_email=email) | Q(email=email)).exists():
            raise forms.ValidationError("Пользователь с данным Email отсутствует в базе данных")
        return email



class UserPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(label="Старый пароль", widget=forms.PasswordInput(attrs=COMMON_TEXT_INPUT_ATTRS))
    new_password1 = forms.CharField(label="Новый пароль", widget=forms.PasswordInput(attrs=COMMON_TEXT_INPUT_ATTRS))
    new_password2 = forms.CharField(label="Подтверждение пароля",
                                    widget=forms.PasswordInput(attrs=COMMON_TEXT_INPUT_ATTRS))



class ReserveEmailForm(forms.ModelForm):
    reserve_email = forms.EmailField(label='Резервная почта', widget=forms.EmailInput(attrs={
        **COMMON_TEXT_INPUT_ATTRS,
        'placeholder': 'Введите резервный Email',
        'style': 'width: 55%;',
    }),
                                     )

    class Meta:
        model = get_user_model()
        fields = ['reserve_email']

    def clean_reserve_email(self):
        reserve_email = self.cleaned_data.get('reserve_email')
        if get_user_model().objects.filter(Q(reserve_email=reserve_email) | Q(email=reserve_email)).exists():
            raise forms.ValidationError(
                "Этот email уже зарегистрирован")
        return reserve_email

class SecretQuestionForm(forms.ModelForm):
    SECRET_CHOICES = [('', 'Выберите вопрос')] + SecurityQuestion.SecretQuestions.choices
    question = forms.ChoiceField(choices=SECRET_CHOICES, label='Контрольный вопрос',
                               widget=forms.Select(attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Выберите контрольный вопрос'}))
    secret_answer=forms.CharField(label="Ответ на контрольный вопрос", min_length=2, widget=forms.TextInput(
        attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите ответ'}))

    class Meta:
        model=SecurityQuestion
        fields = ['question', 'secret_answer']


class SecretQuestionVerifyForm(forms.Form):
    secret_answer = forms.CharField(label="Ответ на контрольный вопрос", widget=forms.TextInput(
        attrs={**COMMON_TEXT_INPUT_ATTRS, 'placeholder': 'Введите ответ'}))
