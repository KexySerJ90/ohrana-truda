from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from simple_history.admin import SimpleHistoryAdmin
from .models import SubjectCompletion, UserAnswer, SentMessage, Notification, Notice, MailDevice, OTP, Profession, \
    Equipment, SecurityQuestion, UserLoginHistory, WorkingConditions, JobDetails, Profile

admin.site.register(get_user_model(), UserAdmin)
admin.site.register(OTP)


@admin.register(SubjectCompletion)
class SubjectCompletionAdmin(SimpleHistoryAdmin):
    fields = ['user_fio', 'user_department', 'subjects', 'study_completed', 'completed', 'score', 'user_calculate_date']
    list_display = ['user_fio', 'user_department', 'subjects', 'slide_order', 'study_completed', 'completed',
                    'user_calculate_date']
    readonly_fields = ['user_department', 'user_calculate_date', 'user_fio']
    actions = ['reset_current_slide', 'reset_current_test']
    ordering = ['users__cat2', 'users', '-completed']
    search_fields = ['users__cat2__name', 'users__last_name', 'users__username']
    list_select_related = ['users', 'subjects', 'current_slide']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Используем prefetch_related для оптимизации запросов
        return queryset.prefetch_related('users__cat2')

    @admin.display(description="Номер слайда")
    def slide_order(self, obj: SubjectCompletion):
        # Проверяем, есть ли текущий слайд и возвращаем его номер, если он существует
        if obj.current_slide:
            return obj.current_slide.order
        return None  # Если слайда нет, возвращаем None или можете вернуть пустую строку

    @admin.display(description="Отделение")
    def user_department(self, obj: SubjectCompletion):
        if obj.users.cat2:
            return obj.users.cat2
        return None

    @admin.display(description="ФИО")
    def user_fio(self, obj: SubjectCompletion):
        if obj.users.first_name and obj.users.first_name:
            return f'{obj.users.first_name} {obj.users.last_name} ({obj.users.username})'
        return None

    @admin.display(description="Дней до отстранения")
    def user_calculate_date(self, obj: SubjectCompletion):
        if not obj.completed:
            if obj.users.calculate_date() > 0:
                return obj.users.calculate_date()
            return 'Работника необходимо отстранить'
        return 'Обучение пройдено'

    @admin.action(description='Сбросить прогресс обучения')
    def reset_current_slide(self, request, queryset):
        updated_count = queryset.update(current_slide=None, study_completed=False)
        self.message_user(request, f'Успешно сброшено {updated_count} текущих слайдов.')

    @admin.action(description='Сбросить тестирование')
    def reset_current_test(self, request, queryset):
        updated_count = queryset.update(completed=False, score=0)
        self.message_user(request, f'Успешно сброшено {updated_count} тестирование')


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    readonly_fields = ['user_completion', 'question', 'selected_answer']
    ordering = ['user_completion']
    list_select_related = ['user_completion', 'question']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Используем prefetch_related для оптимизации запросов
        return queryset.prefetch_related('user_completion__subjects', 'user_completion__users')


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


@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    search_fields = ['name']
    prepopulated_fields = {"slug": ("name",)}
    ordering = ['name']


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    search_fields = ['name']
    ordering = ['name']
    list_filter = ['siz__name']

@admin.register(SecurityQuestion)
class SecurityQuestionAdmin(admin.ModelAdmin):
    readonly_fields = ['user', 'question']

@admin.register(UserLoginHistory)
class UserLoginHistoryAdmin(admin.ModelAdmin):
    readonly_fields = ['user', 'login_time','ip_address','location','device_type','browser','os']
    list_filter = ['user']
    list_select_related = ['user']


@admin.register(WorkingConditions)
class WorkingConditionsAdmin(admin.ModelAdmin):
    pass


@admin.register(JobDetails)
class JobDetailsAdmin(SimpleHistoryAdmin):
    search_fields = ['profession']
    list_filter = ['department','working_conditions']
    list_select_related = ['profession','department']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    readonly_fields = ['user','patronymic','profession','photo','post_photo','date_birth','date_of_work']
    list_filter=['user']

    @admin.display(description="Изображение", ordering='content')
    def post_photo(self, profile: Profile):
        if profile.photo:
            return mark_safe(f"<img src='{profile.photo.url}' width=50>")
        return "Без фото"