from django.contrib.auth.views import LogoutView, PasswordChangeView, PasswordChangeDoneView, PasswordResetView, \
    PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.urls import path, reverse_lazy
from . import views
from .forms import UserForgotPasswordForm

app_name = "users"

urlpatterns = [
    path('login/', views.LoginUser.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password-change/', views.UserPasswordChange.as_view(), name="password_change"),
    path('password-change/done/', PasswordChangeDoneView.as_view(template_name="users/password_change_done.html"), name="password_change_done"),
    path('password-reset/',
         views.UserPasswordResetView.as_view(
            template_name="users/password_reset_form.html",
            email_template_name="users/password_reset_email.html",
            success_url = reverse_lazy("users:password_reset_done", ),
            form_class=UserForgotPasswordForm,
         ),
         name='password_reset'),
    path('password-reset/done/',
         PasswordResetDoneView.as_view(template_name="users/password_reset_done.html"),
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         views.UserPasswordResetConfirmView.as_view(
            template_name="users/password_reset_confirm.html",
            success_url=reverse_lazy("users:password_reset_complete")
         ),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         PasswordResetCompleteView.as_view(template_name="users/password_reset_complete.html"),
         name='password_reset_complete'),

    path('register/', views.RegisterUser.as_view(), name='register'),
    path('result/', views.MyResult.as_view(), name='result'),
    path('leader/', views.LeaderResultsView.as_view(), name='leader_results'),
    path('profile/', views.ProfileUser.as_view(), name='profile'),
    path('editprofile/', views.EditProfileUser.as_view(), name='edit_profile'),
    path('settings/', views.SettingsUser.as_view(), name = 'settings_user'),
    path('email-verification/<str:uidb64>/<str:token>/', views.email_verification, name='email-verification'),
    path('email-verification-sent', views.email_verification_sent, name='email-verification-sent'),
    path('email-verification-success', views.email_verification_success, name='email-verification-success'),
    path('email-verification-failed', views.email_verification_failed, name='email-verification-failed'),
    path('welcome_social/', views.Welcome_social.as_view(), name='welcome_social'),
    path('contact/', views.contact_view, name='contact'),
    path('verify_otp/', views.VerifyOTPView.as_view(), name='verify_otp'),
    path('resend-otp/', views.ResendOtpView.as_view(), name='resend_otp'),
    path('siz/', views.SIZForm.as_view(), name='siz'),
    path('get_equipment/', views.EquipmentListView.as_view(), name='get_equipment'),
    path('reserve-email/', views.ReserveMailView.as_view(), name='reserve_email'),
    path('token-verification-reserve-email/', views.TokenVerificationReserveEmailView.as_view(), name='token_verification_reserve_email'),
    path('delete-reserve-email/', views.delete_reserve_email, name='delete_reserve_email'),
    path('secretquestion/', views.SecretQuestionView.as_view(), name='secretquestion'),
    path('secretquestion-verify/', views.UserSecretQuestionVerify.as_view(), name='secretquestion_verify'),
    path('delete-secret-answer/', views.delete_secret_answer, name='delete_secret_answer'),
    path('login-history/', views.LoginHistoryView.as_view(), name='login_history'),
    path('sout-user/', views.SOUTUserView.as_view(), name='sout_user'),

]
