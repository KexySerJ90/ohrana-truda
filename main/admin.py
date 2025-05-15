from django.contrib import admin, messages
from django.db.models import Q
from django.utils.safestring import mark_safe
from django_mptt_admin.admin import DjangoMpttAdmin
from simple_history.admin import SimpleHistoryAdmin
from django import forms

from main.models import Categorys, UploadFiles, Article, Rating, TagPost, \
    Comment, UniqueView, Notification, Notice, UserLoginHistory, SentMessage
from main.utils import validate_file
from users.models import Departments


class CustomUploadFileAdminForm(forms.ModelForm):
    class Meta:
        model = UploadFiles
        fields = ['cat', 'title', 'file', 'is_common', 'description']  # поля, которые будут отображаться в форме

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')  # получаем файл из очищенных данных
        if file:
            validate_file(file)
        return cleaned_data


@admin.register(Categorys)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ['name']
    prepopulated_fields = {"slug": ("name",)}


@admin.register(TagPost)
class TagPostAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("tag",)}


@admin.register(UploadFiles)
class UploadFilesAdmin(admin.ModelAdmin):
    list_select_related = ['cat']
    list_filter = ['cat']
    search_fields = ['cat__name', 'title']
    ordering = ['cat', '-uploaded_at']
    readonly_fields = ['is_common', 'uploaded_at']
    form = CustomUploadFileAdminForm
    actions = ['delete_is_common_files']

    def save_model(self, request, obj, form, change):
        if not change:  # Если создается новый объект
            category = obj.cat
            is_common = category.is_inpatient

            if is_common:
                departments = Departments.objects.filter(Q(is_inpatient=is_common))
                first_department = departments.first()

                # Создаем общую запись
                common_upload = UploadFiles.objects.create(
                    cat=first_department,
                    file=obj.file,
                    is_common=True
                )
                # Создаем ссылки на общий файл для остальных отделений
                for department in departments.exclude(pk=first_department.pk):
                    UploadFiles.objects.create(
                        cat=department,
                        file=common_upload.file,
                        is_common=True
                    )
            else:
                # Создаем отдельную запись для амбулаторного отделения
                obj.save()
        else:
            obj.save()

    @admin.action(description='Удалить общие файлы с одинаковыми именами')
    def delete_is_common_files(self, request, queryset):
        files_to_delete = queryset.filter(is_common=True).values_list('file', flat=True).distinct()
        # Удаляем все записи с этими файлами и флагом is_common = True
        num_deleted, _ = UploadFiles.objects.filter(file__in=files_to_delete, is_common=True).delete()
        # Удаление найденных записей
        message_bit = f"{num_deleted} файлов были успешно удалены"
        self.message_user(request, message_bit)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_select_related = ['post', 'user']
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


@admin.register(Article)
class ArticleAdmin(SimpleHistoryAdmin):
    fields = ['title', 'slug', 'content', 'photo', 'post_photo', 'category', 'tags', 'views', 'is_published']
    readonly_fields = ['post_photo', 'views']
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


@admin.register(UniqueView)
class UniqueViewAdmin(admin.ModelAdmin):
    search_fields = ['article']
    readonly_fields = ['article', 'ip_address', 'timestamp']
    list_filter = ['ip_address', 'article']
    list_select_related = ['article']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    fields = ['user', 'comment', 'is_read']
    search_fields = ['user__username']
    readonly_fields = ['user', 'comment', 'is_read']
    list_select_related = ['user', 'comment']
    list_filter = ['user']


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    fields = ['user', 'message', 'is_read']
    search_fields = ['user__username']
    readonly_fields = ['user']
    list_select_related = ['user']
    list_filter = ['user', 'is_read']


@admin.register(UserLoginHistory)
class UserLoginHistoryAdmin(admin.ModelAdmin):
    readonly_fields = ['user', 'login_time', 'ip_address', 'location', 'device_type', 'browser', 'os']
    list_filter = ['user']
    list_select_related = ['user']


@admin.register(SentMessage)
class SentMessageAdmin(admin.ModelAdmin):
    list_select_related = ['user']
    readonly_fields = ['user', 'purpose', 'timestamp']
    list_filter = ['user', 'purpose']
