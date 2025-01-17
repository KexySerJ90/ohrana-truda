from datetime import timedelta

import pyotp
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetConfirmView, PasswordResetView
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic import CreateView, UpdateView, ListView, DetailView, FormView
from ohr import settings
from .forms import LoginUserForm, RegisterUserForm, ProfileUserForm, UserPasswordChangeForm, WelcomeSocialForm, \
    ContactForm, OTPForm, ProfessionForm, ReserveEmailForm, SecretQuestionForm, SecretQuestionVerifyForm, \
    UserForgotPasswordForm
from .models import SentMessage, MailDevice, OTP, Profession, SecurityQuestion, UserLoginHistory, JobDetails
from .permissions import ProfileRequiredMixin, StatusRequiredMixin, NotSocialRequiredMixin
from .token import user_tokenizer_generate
from django.core.mail import send_mail
from ohr.settings import EMAIL_HOST_USER, EMAIL_RECIPIENT_LIST, PHONE, AUTO_LOGOUT
from .utils import UserQuerysetMixin, send_message, login_required_redirect, generate_otp, BaseUserView, sent_count
from typing import Optional, Any, Dict


class LoginUser(ProfileRequiredMixin, LoginView):
    form_class = LoginUserForm
    template_name = 'users/login.html'
    extra_context = {'title': 'Авторизация'}

    def get_success_url(self) -> str:
        return self.request.GET.get('next', reverse_lazy('users:profile'))

    def form_valid(self, form: LoginUserForm) -> Any:
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(144000)
        else:
            self.request.session.set_expiry(AUTO_LOGOUT['IDLE_TIME'])
        self.request.session.modified = True
        user = form.get_user()  # Получаем пользователя из формы
        if user and user.two_factor_enabled and not user.is_social_user:
            # Проверка наличия cookie
            if self.request.COOKIES.get('2fa_verified') == user.hashed_id():
                login(self.request, user)
                return redirect('users:profile')

            # Генерация OTP
            otp_secret, otp_code = generate_otp()
            otp_obj, created = OTP.objects.get_or_create(user=user, email=user.email)
            otp_obj.otp_secret = otp_secret
            otp_obj.save()
            device = MailDevice.objects.create(user=user, name=f'2fa-{user.username}')
            device.save()
            send_message('Ваш код подтверждения', EMAIL_HOST_USER, otp_code, user)
            print(otp_code)
            self.request.session['user_email'] = user.email
            self.request.session['otp_sent_time'] = timezone.now().isoformat()
            self.request.session['user_id'] = user.hashed_id()
            return redirect('users:verify_otp')

        return super().form_valid(form)


class VerifyOTPView(FormView):
    template_name = 'users/verify_otp.html'
    form_class = OTPForm
    success_url = reverse_lazy('users:profile')
    extra_context = {'title': 'Верификация OTP'}

    def form_valid(self, form):
        enter_otp_code = form.cleaned_data['otp']
        user_email = self.request.session.get('user_email')
        user_id = self.request.session.get('user_id')
        otp_obj = OTP.objects.filter(email=user_email).first()

        if otp_obj:
            otp = pyotp.TOTP(otp_obj.otp_secret, interval=3000)
            if otp.verify(enter_otp_code):
                otp_obj.is_verified = True
                otp_obj.save()
                user = get_user_model().objects.get(email=user_email)
                if user:
                    login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
                    response = super().form_valid(form)
                    del self.request.session['user_email']
                    response.set_cookie('2fa_verified', user_id, httponly=True, samesite='Lax',
                                        expires=timezone.now() + timedelta(days=10))
                    return response

        form.add_error('otp', 'Неверный код подтверждения.')
        return self.form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        # Проверяем, авторизован ли пользователь
        if request.user.is_authenticated or not request.session.get('user_email'):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ResendOtpView(View):
    def post(self, request):
        user_email = request.session.get('user_email')
        if user_email:
            otp_obj = OTP.objects.filter(email=user_email).first()
            if otp_obj:
                user = get_user_model().objects.get(email=user_email)
                if user:
                    count=sent_count(user, SentMessage.PURPOSE.RESET)
                    if count >= 3:
                        return JsonResponse(
                            {'success': False,
                             'message': 'Вы достигли лимита отправки сообщений за последние 30 минут.'})

                    # Генерация нового OTP
                    otp_secret, otp_code = generate_otp()

                    # Обновляем секрет и сохраняем
                    otp_obj.otp_secret = otp_secret
                    otp_obj.save()

                    # Отправляем новый код
                    send_message('Ваш новый код подтверждения', EMAIL_HOST_USER, otp_code, user)
                    SentMessage.objects.create(user=user, purpose=SentMessage.PURPOSE.RESET)
                    return JsonResponse({'success': True, 'message': 'Код подтверждения отправлен.'})
        return JsonResponse({'success': False, 'message': 'Не удалось отправить код.'})


class RegisterUser(ProfileRequiredMixin, CreateView, BaseUserView):
    form_class = RegisterUserForm
    template_name = 'users/register.html'
    extra_context = {'title': "Регистрация"}
    success_url = reverse_lazy('users:email-verification-sent')

    @transaction.atomic
    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        if not user.phone:
            user.phone = None
        user.save()
        current_site = get_current_site(self.request)
        subject = 'Верификация email'

        message = render_to_string('users/email-verification.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': user_tokenizer_generate.make_token(user),
        })
        user.email_user(subject=subject, message=message)
        self.handle_subjects(user)
        self.request.session['user_mail'] = form.cleaned_data.get('email')
        self.request.session['user_username'] = form.cleaned_data.get('username')
        return super().form_valid(form)


class ProfileUser(LoginRequiredMixin, DetailView):
    template_name = 'users/profile.html'
    model = get_user_model()
    extra_context = {'title': "Личный кабинет"}

    def get_object(self, queryset=None):
        return self.request.user


class EditProfileUser(LoginRequiredMixin, StatusRequiredMixin, UpdateView):
    model = get_user_model()
    form_class = ProfileUserForm
    template_name = 'users/edit_profile.html'
    extra_context = {
        'title': "Профиль пользователя",
        'default_image': settings.DEFAULT_USER_IMAGE,
    }

    def get_success_url(self) -> str:
        return reverse_lazy('users:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form: ProfileUserForm) -> JsonResponse:
        response = super().form_valid(form)
        return JsonResponse({'success': True})

    def form_invalid(self, form: ProfileUserForm) -> JsonResponse:
        return JsonResponse(form.errors, status=400)


class SettingsUser(LoginRequiredMixin, NotSocialRequiredMixin, DetailView):
    template_name = 'users/settings.html'
    model = get_user_model()
    extra_context = {'title': "Настройки", }

    def get_object(self, queryset=None):
        return self.request.user

    def post(self, request, *args, **kwargs) -> JsonResponse:
        user = self.get_object()
        user.two_factor_enabled = not user.two_factor_enabled  # Переключаем состояние
        user.save()

        status_message = "включена" if user.two_factor_enabled else "выключена"
        # Возвращаем JsonResponse с новым статусом
        return JsonResponse({'status': 'success', 'message': f'Двухфакторная авторизация {status_message}.',
                             'new_status': user.two_factor_enabled})


class MyResult(LoginRequiredMixin, StatusRequiredMixin, ListView):
    model = get_user_model()
    template_name = 'users/results.html'
    extra_context = {'title': "Мои результаты"}

    # def get_queryset(self):
    #     user = self.request.user
    #     return User.objects.prefetch_related('subject_completions__subjects').filter(pk=user.pk)

    def get_object(self, queryset=None):
        return self.request.user


class LeaderResultsView(LoginRequiredMixin, ListView, UserQuerysetMixin):
    template_name = 'users/leader_results.html'
    paginate_by = 4
    context_object_name = 'users'
    extra_context = {'title': "Результаты подразделения"}

    def get_queryset(self):
        user = self.request.user
        return self.get_user_queryset(user)


def email_verification(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    unique_id = force_str(urlsafe_base64_decode(uidb64))
    user = get_user_model().objects.get(pk=unique_id)
    if user and user_tokenizer_generate.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect('users:email-verification-success')
    return redirect('users:email-verification-failed')


@login_required_redirect
def email_verification_sent(request: HttpRequest) -> HttpResponse:
    return render(request, 'users/email-verification-sent.html')


def email_verification_success(request: HttpRequest) -> HttpResponse:
    send_mail(
        subject='Успешная регистрация',
        message=f"Поздравляю, {request.session['user_username']}, Вы прошли успещную регистрацию на сайте {request.get_host()}.\n\n"
                "Если у вас возникнут вопросы или потребуется помощь, наша команда поддержки всегда готова помочь вам!",
        from_email=EMAIL_HOST_USER,
        recipient_list=[request.session['user_mail']],
    )
    del request.session['user_mail']
    del request.session['user_username']
    return render(request, 'users/email-verification-success.html')


@login_required_redirect
def email_verification_failed(request: HttpRequest) -> HttpResponse:
    return render(request, 'users/email-verification-failed.html')


class Welcome_social(UpdateView, BaseUserView):
    model = get_user_model()
    form_class = WelcomeSocialForm
    template_name = 'users/welcome_social.html'
    extra_context = {'title': "Приветствие"}

    def get_success_url(self) -> str:
        return self.request.GET.get('next', reverse_lazy('users:profile'))

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.user.status:
            return redirect('users:profile')
        if 'form_not_saved' not in request.session:
            request.session['form_not_saved'] = True

        return super().get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user

    # def get_initial(self):
    #     initial = super().get_initial()
    #     # Предположим, что у вас есть объект пользователя, данные которого вы хотите использовать.
    #     user = self.request.user  # Или другой способ получения пользователя
    #
    #     if hasattr(user, 'social_auth'):
    #         # Получаем все социальные аккаунты пользователя
    #         social_accounts = user.social_auth.all()
    #
    #         # Проверяем, есть ли среди них аккаунт GitHub
    #         if any(account.provider == 'github' for account in social_accounts):
    #             # Устанавливаем начальные значения для полей формы только если авторизация произошла через GitHub
    #             initial['username'] = user.username
    #             initial['email'] = user.email
    #
    #     return initial

    @transaction.atomic
    def form_valid(self, form):
        user = form.save()
        # del self.request.session['form_not_saved']
        self.request.session['form_not_saved'] = False
        self.handle_subjects(user)

        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not request.user.is_social_user:
            return redirect('users:profile')
        return super().dispatch(request, *args, **kwargs)


@login_required
def contact_view(request: HttpRequest) -> HttpResponse:
    initial_data = {
        'username': request.user.username,
        'email': request.user.email}
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            # Проверка на количество отправленных сообщений за день
            today = timezone.now().date()
            sent_count = SentMessage.objects.filter(user=request.user, timestamp__date=today, purpose=SentMessage.PURPOSE.CONTACT).count()

            if sent_count >= 3:
                return render(request, 'users/contact_form.html', {
                    'form': form,
                    'error': 'Вы достигли лимита отправки сообщений на сегодня.'
                })
            # Формирование текста сообщения
            full_message = f"Имя: {username}\nEmail: {email}\nСообщение:\n{message}"
            # Отправка письма администратору
            send_mail(
                subject='Обратная связь',
                message=full_message,
                from_email=EMAIL_HOST_USER,
                recipient_list=[EMAIL_RECIPIENT_LIST],
            )
            # Сохранение информации о отправленном сообщении
            SentMessage.objects.create(user=request.user, purpose=SentMessage.PURPOSE.CONTACT)
            return render(request, 'users/contact_success.html')  # Страница успешной отправки
    else:
        form = ContactForm(initial=initial_data)
    return render(request, 'users/contact_form.html', {'form': form, 'phone': PHONE})


class SIZForm(LoginRequiredMixin, FormView):
    template_name = 'users/siz_form.html'
    form_class = ProfessionForm
    extra_context = {'title': "Калькулятор СИЗ"}


class EquipmentListView(LoginRequiredMixin, View):
    def get(self, request) -> JsonResponse:
        profession_id = request.GET.get('profession_id')
        equipment_list = []

        if profession_id:
            profession = Profession.objects.get(id=profession_id)
            equipment_queryset = profession.equipment.all()

            for equipment in equipment_queryset:
                equipment_list.append({
                    'description': equipment.description,
                    'quantity': equipment.quantity,
                })

        return JsonResponse({'equipment': equipment_list})


class ReserveMailView(LoginRequiredMixin, NotSocialRequiredMixin, FormView):
    form_class = ReserveEmailForm
    template_name = 'users/reserve-email.html'

    def form_valid(self, form):
        user = self.request.user
        subject = 'Резервный email'
        reserve_email = form.cleaned_data['reserve_email']
        current_site = get_current_site(self.request)
        otp_secret, otp_code = generate_otp()
        message = render_to_string('users/reserve-email-verification.html', {
            'user': user,
            'domain': current_site.domain,
            'token': otp_code,
            'email': user.email,
        })
        print(otp_code)
        send_mail(
            subject=subject,
            message=message,
            from_email=EMAIL_HOST_USER,
            recipient_list=[reserve_email],
        )
        self.request.session['reserve_email'] = reserve_email
        self.request.session['otp_sec'] = otp_secret

        return JsonResponse({'status': 'success', 'message': 'Код отправлен на резервный Email.'})

    def form_invalid(self, form):
        return JsonResponse(
            {'status': 'error', 'message': 'Этот Email уже присутствует в базе, либо введён некорректно'}, status=400)


class TokenVerificationReserveEmailView(LoginRequiredMixin, View):
    def post(self, request):
        user = self.request.user
        enter_otp_code = request.POST.get('token')
        otp_secret = self.request.session.get('otp_sec')
        reserve_email = self.request.session.get('reserve_email')
        if otp_secret:
            otp = pyotp.TOTP(otp_secret, interval=3000)
            if otp.verify(enter_otp_code):
                user.reserve_email = reserve_email
                user.save()
                del self.request.session['otp_sec']
                del self.request.session['reserve_email']
                return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Неверный код подтверждения.'})


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    def form_valid(self, form):
        user = form.save()
        user.two_factor_enabled = False
        user.save()
        # send_mail(
        #     subject='Изменение пароля',
        #     message=f'{user.username}, {timezone.now()} поменял пароль. Если вы этого не делали, то срочно свяжитесь с администрацией сайта {get_current_site(self.request)}',
        #     from_email=EMAIL_HOST_USER,
        #     recipient_list=[user.email, user.reserve_email],
        # )
        return super().form_valid(form)


class SecretQuestionView(LoginRequiredMixin, UpdateView):
    template_name = 'users/secret_question_form.html'
    form_class = SecretQuestionForm
    extra_context = {'title': "Секретный вопрос"}
    success_url = reverse_lazy('users:settings_user')
    model = get_user_model()

    def get_object(self, queryset=None):
        return self.request.user

    def get_initial(self):
        initial = super().get_initial()
        initial['secret_answer'] = None  # Устанавливаем секретный ответ пустым
        return initial

    def form_valid(self, form):
        user = self.get_object()
        question = form.cleaned_data.get('question')
        answer = self.request.POST.get('secret_answer')
        hashed_answer = make_password(answer)
        user.secret_answer = hashed_answer
        sec_question, created = SecurityQuestion.objects.update_or_create(
            user=user,
            defaults={'question': question}
        )
        if 'sec_user_verify' in self.request.session:
            del self.request.session['sec_user_verify']
        response = super().form_valid(form)
        # send_mail(
        #     subject='Вы добавили/изменили контрольный вопрос',
        #     message=f'{user.username}, {timezone.now()} добавили/изменили контрольный вопрос. Если вы этого не делали, то срочно свяжитесь с администрацией сайта {get_current_site(self.request)}',
        #     from_email=EMAIL_HOST_USER,
        #     recipient_list=[user.email],
        # )
        return response

    def dispatch(self, request, *args, **kwargs):
        user = self.get_object()
        if user.secret_answer and not self.request.session.get('sec_user_verify'):
            return redirect('users:secretquestion_verify')
        if user.is_social_user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class UserPasswordChange(PasswordChangeView):
    form_class = UserPasswordChangeForm
    success_url = reverse_lazy("users:password_change_done")
    template_name = "users/password_change_form.html"

    def form_valid(self, form: UserPasswordChangeForm):
        # Вызываем метод родительского класса для обработки формы
        response = super().form_valid(form)
        send_mail(
            subject='Изменение пароля',
            message=f'{self.request.user}, {timezone.now()} поменял пароль. Если вы этого не делали, то срочно свяжитесь с администрацией сайта {get_current_site(self.request)}',
            from_email=EMAIL_HOST_USER,
            recipient_list=[self.request.user.email],
        )
        return response


class UserPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        email = form.cleaned_data["email"]
        user = get_user_model().objects.get(Q(reserve_email=email) | Q(email=email))
        count = sent_count(user, purpose=SentMessage.PURPOSE.RESCUE)
        if count >= 3:
            messages.error(self.request, 'Вы достигли лимита отправки сообщений на данную элеутронную почту за последние 30 минут.')
            return self.form_invalid(form)
        if not user.secret_answer:
            SentMessage.objects.create(user=user,is_rescue=True)
            return super().form_valid(form)
        self.request.session['sec_user_email'] = email
        SentMessage.objects.create(user=user, purpose=SentMessage.PURPOSE.RESCUE)
        return redirect(reverse_lazy('users:secretquestion_verify'))


class UserSecretQuestionVerify(NotSocialRequiredMixin, PasswordResetView, FormView):
    template_name = 'users/secret_question_form.html'
    form_class = SecretQuestionVerifyForm
    success_url = reverse_lazy("users:password_reset_done", )
    email_template_name = "users/password_reset_email.html"

    def form_valid(self, form):
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': self.extra_email_context,
        }
        secret_answer = form.cleaned_data['secret_answer']
        if not self.request.user.is_anonymous:
            user_email = self.request.user.email
        else:
            user_email = self.request.session.get('sec_user_email')
        user = get_user_model().objects.get(Q(reserve_email=user_email) | Q(email=user_email))
        if check_password(secret_answer, user.secret_answer):
            if not self.request.user.is_anonymous and not 'delete_secret_answer' in self.request.session:
                self.request.session['sec_user_verify'] = True
                return redirect('users:secretquestion')
            if 'delete_secret_answer' in self.request.session:
                deleted_secret_answer = SecurityQuestion.objects.get(user=user)
                deleted_secret_answer.delete()
                del self.request.session['delete_secret_answer']
                if 'sec_user_verify' in self.request.session:
                    del self.request.session['sec_user_verify']
                # send_mail(
                #     subject='Удаление секретного вопроса',
                #     message=f'{user.username}, Вы удалили секретный вопрос для восстановления данных аккаунта.\n\n'
                #             'Если Вы этого не деали, срочно свяжитесь с нами',
                #     from_email=EMAIL_HOST_USER,
                #     recipient_list=[user.email],
                # )

                return redirect('users:settings_user')
            # Если ответ верный, создаем экземпляр PasswordResetForm
            password_reset_form = UserForgotPasswordForm({'email': user_email})
            if password_reset_form.is_valid():
                # Отправляем электронное письмо со сбросом пароля
                password_reset_form.save(**opts)
                del self.request.session['sec_user_email']
                return redirect(self.success_url)
        form.add_error('secret_answer', 'Ответ неверный')
        return self.form_invalid(form)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user_email = self.request.session.get(
            'sec_user_email') if self.request.user.is_anonymous else self.request.user.email
        user = get_user_model().objects.get(Q(reserve_email=user_email) | Q(email=user_email))
        context['securityquestion'] = get_object_or_404(SecurityQuestion, user=user)
        context['title'] = 'Проверка контрольного вопроса'
        return context


@login_required
def delete_reserve_email(request):
    user = request.user
    user.reserve_email = None
    user.save()
    send_mail(
        subject='Удаление резервного Email',
        message=f'{user.username}, Вы удалили резервную почту для восстановления данных аккаунта.\n\n'
                'Если Вы этого не деали, срочно свяжитесь с нами',
        from_email=EMAIL_HOST_USER,
        recipient_list=[user.email],
    )
    messages.success(request, 'Резервный email успешно удален.')
    return redirect('users:settings_user')


@login_required
def delete_secret_answer(request):
    request.session['delete_secret_answer'] = True
    return redirect('users:secretquestion_verify')


class LoginHistoryView(LoginRequiredMixin, ListView):
    model = UserLoginHistory
    template_name = 'users/login_history.html'
    context_object_name = 'history'
    ordering = ['-login_time']
    paginate_by = 20

    def get_queryset(self):
        # Фильтруем историю входов для текущего пользователя
        return super().get_queryset().filter(user=self.request.user)


class SOUTUserView(LoginRequiredMixin, DetailView):
    template_name = 'users/sout.html'
    model = JobDetails
    extra_context = {'title': "Результаты специальной оценки условий труда"}
    context_object_name = 'workplace'

    def get_object(self, queryset=None):
        user = self.request.user
        try:
            # Получаем рабочее место по профессии и отделению текущего пользователя
            obj = JobDetails.objects.get(
                profession=user.profession,
                department=user.cat2
            )
        except JobDetails.DoesNotExist:
            obj = None
        return obj
