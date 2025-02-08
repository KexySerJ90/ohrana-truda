from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from .models import MailDevice, OTP, Profession, \
    SecurityQuestion, Profile, Departments

admin.site.register(get_user_model(), UserAdmin)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    readonly_fields = ['user', 'otp_secret', 'email']
    list_filter = ['user', 'is_verified']


@admin.register(MailDevice)
class EmailDeviceAdmin(admin.ModelAdmin):
    readonly_fields = ['user']
    list_select_related = ['user']
    list_filter = ['user']


@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    search_fields = ['name']
    ordering = ['name']
    actions = ['copy_profession']
    list_filter = ['worker']


    @admin.action(description='Копировать похожие профессии')
    def copy_profession(self, request, queryset):
        for obj in queryset:
            new_obj = Profession(name=f"Копия {obj.name}")
            new_obj.save()  # Сначала сохраняем объект

            # Затем устанавливаем оборудование через .set()
            new_obj.equipment.set(obj.equipment.all())
        message_bit = "Экземпляры профессий скопированы"
        self.message_user(request, message_bit)

@admin.register(SecurityQuestion)
class SecurityQuestionAdmin(admin.ModelAdmin):
    readonly_fields = ['user', 'question']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # readonly_fields = ['user','patronymic','profession','photo','post_photo','date_birth']
    list_filter=['user']

    @admin.display(description="Изображение", ordering='content')
    def post_photo(self, profile: Profile):
        if profile.photo:
            return mark_safe(f"<img src='{profile.photo.url}' width=50>")
        return "Без фото"


@admin.register(Departments)
class DepartmentsAdmin(admin.ModelAdmin):
    search_fields = ['name']
    prepopulated_fields = {"slug": ("name",)}
    ordering = ['name']