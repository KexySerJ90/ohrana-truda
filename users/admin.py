from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from .models import SentMessage, Notification, Notice, MailDevice, OTP, Profession, \
    SecurityQuestion, UserLoginHistory, Profile
admin.site.register(get_user_model(), UserAdmin)
admin.site.register(OTP)


@admin.register(SentMessage)
class SentMessageAdmin(admin.ModelAdmin):
    list_select_related = ['user']
    readonly_fields = ['user', 'purpose']
    list_filter = ['purpose']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    fields = ['user', 'comment', 'is_read']
    search_fields = ['user__username']
    readonly_fields = ['user', 'comment']
    list_select_related = ['user', 'comment']


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    fields = ['user', 'message', 'is_read']
    search_fields = ['user__username']
    readonly_fields = ['user']
    list_select_related = ['user']


@admin.register(MailDevice)
class EmailDeviceAdmin(admin.ModelAdmin):
    readonly_fields = ['user']
    list_select_related = ['user']


@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    search_fields = ['name']
    ordering = ['name']


@admin.register(SecurityQuestion)
class SecurityQuestionAdmin(admin.ModelAdmin):
    readonly_fields = ['user', 'question']

@admin.register(UserLoginHistory)
class UserLoginHistoryAdmin(admin.ModelAdmin):
    readonly_fields = ['user', 'login_time','ip_address','location','device_type','browser','os']
    list_filter = ['user']
    list_select_related = ['user']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # readonly_fields = ['user','patronymic','profession','photo','post_photo','date_birth']
    list_filter=['user']

    @admin.display(description="Изображение", ordering='content')
    def post_photo(self, profile: Profile):
        if profile.photo:
            return mark_safe(f"<img src='{profile.photo.url}' width=50>")
        return "Без фото"