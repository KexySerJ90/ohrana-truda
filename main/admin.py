from django.contrib import admin, messages
from django.utils.safestring import mark_safe
from django_mptt_admin.admin import DjangoMpttAdmin
from simple_history.admin import SimpleHistoryAdmin

from main.models import Categorys, UploadFiles, Subject, Article, Departments, Rating, Question, Slide, TagPost, Video, \
    Answer, Comment


@admin.register(Categorys)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ['name']
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Departments)
class DepartmentsAdmin(admin.ModelAdmin):
    search_fields = ['name']
    prepopulated_fields = {"slug": ("name",)}
    ordering = ['name']


@admin.register(TagPost)
class TagPostAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("tag",)}


@admin.register(UploadFiles)
class UploadFilesAdmin(admin.ModelAdmin):
    list_select_related=['cat']
    list_filter = ['cat']
    search_fields = ['cat__name']
    ordering = ['cat', '-uploaded_at']
    readonly_fields = ['is_common']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_select_related=['subject']


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_select_related = ['post','user']
    list_filter = ['user', 'post']
    readonly_fields = []

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        # Получаем все поля модели
        self.readonly_fields = [field.name for field in model._meta.get_fields()]

@admin.register(Comment)
class CommentAdmin(DjangoMpttAdmin):
    ordering = ['post', '-time_create']
    readonly_fields = ['user']

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    ordering = ['id']


@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = ('subject', 'order', 'post_photo')
    ordering = ['subject', 'order']

    @admin.display(description="Изображение", ordering='content')
    def post_photo(self, slide: Article):
        if slide.photo:
            return mark_safe(f"<img src='{slide.photo.url}' width=50>")
        return "Без фото"


@admin.register(Article)
class ArticleAdmin(SimpleHistoryAdmin):
    fields = ['title', 'slug', 'content', 'photo', 'post_photo', 'category', 'tags','is_published']
    readonly_fields = ['post_photo']
    prepopulated_fields = {"slug": ("title",)}
    filter_vertical = ['tags']
    list_display = ('title', 'post_photo', 'time_create', 'is_published', 'category')
    list_display_links = ('title',)
    list_editable = ('is_published',)
    actions = ['set_published', 'set_draft']
    search_fields = ['title__startswith', 'cat__name']
    save_on_top = True
    list_select_related = ['category']

    @admin.display(description="Изображение", ordering='content')
    def post_photo(self, article: Article):
        if article.photo:
            return mark_safe(f"<img src='{article.photo.url}' width=50>")
        return "Без фото"

    @admin.action(description="Опубликовать выбранные записи")
    def set_published(self, request, queryset):
        count = queryset.update(is_published=Article.Status.PUBLISHED)
        self.message_user(request, f"Изменено {count} записей.")

    @admin.action(description="Снять с публикации выбранные записи")
    def set_draft(self, request, queryset):
        count = queryset.update(is_published=Article.Status.DRAFT)
        self.message_user(request, f"{count} записей сняты с публикации!", messages.WARNING)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    search_fields = ['title']
    prepopulated_fields = {"slug": ("title",)}

