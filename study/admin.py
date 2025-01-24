from django.contrib import admin
from django.utils.safestring import mark_safe
from simple_history.admin import SimpleHistoryAdmin

from main.models import Article
from study.models import Subject, Question, Answer, Slide, Video, UserAnswer, SubjectCompletion


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_select_related=['subject']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    ordering = ['id']
    list_select_related = ['next_video']


@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = ('subject', 'order', 'post_photo')
    ordering = ['subject', 'order']

    @admin.display(description="Изображение", ordering='content')
    def post_photo(self, slide: Article):
        if slide.photo:
            return mark_safe(f"<img src='{slide.photo.url}' width=50>")
        return "Без фото"


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    search_fields = ['title']
    prepopulated_fields = {"slug": ("title",)}


@admin.register(SubjectCompletion)
class SubjectCompletionAdmin(SimpleHistoryAdmin):
    fields = ['user_fio', 'user_department', 'subjects', 'study_completed', 'completed', 'score', 'user_calculate_date']
    list_display = ['user_fio', 'user_department', 'subjects', 'slide_order', 'study_completed', 'completed',
                    'user_calculate_date']
    readonly_fields = ['user_department', 'user_calculate_date', 'user_fio']
    actions = ['reset_current_slide', 'reset_current_test']
    ordering = ['users__cat2', 'users', '-completed']
    search_fields = ['users__cat2__name', 'users__last_name', 'users__username']
    list_select_related = ['subjects', 'current_slide', 'users__profile']

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
            if obj.users.profile.calculate_date() > 0:
                return obj.users.profile.calculate_date()
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