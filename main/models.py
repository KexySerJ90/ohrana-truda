from ckeditor.fields import RichTextField
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator, MaxLengthValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from main.utils import get_upload_path
from users.models import User


class Categorys(models.Model):
    name = models.CharField(max_length=100, db_index=True, verbose_name="Категория")
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('main:category', kwargs={'cat_slug': self.slug})


class Departments(models.Model):
    name = models.CharField(max_length=100, db_index=True, verbose_name="Отделение")
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    is_inpatient = models.BooleanField(default=False, verbose_name='Является стационарным отделением?')

    class Meta:
        verbose_name = "Отделение"
        verbose_name_plural = "Отделения"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('main:maindoc', kwargs={'dep_slug': self.slug})


class Subject(models.Model):
    class TypeOfStudy(models.TextChoices):
        FIRST_AID = ('first_aid', 'Первая помощь пострадавшим')
        SAFE_METHOD1 = ('safe_method1', 'Безопасные методы и приемы выполнения работ для медицинских работников')
        SAFE_METHOD2 = ('safe_method2', 'Безопасные методы и приемы выполнения работ для рабочих профессий')
        SUOT = ('suot', 'Обучение по общим вопросам охраны труда и функционирования системы управления охраной труда')
        SIZ = ('siz', 'СИЗ')
        FIRE_SAFETY = ('fire_safety', 'Пожарная безопаность')
        CIVIL_DEFENSE = ('civil_defense', 'Гражданская оборона')

    title = models.CharField(choices=TypeOfStudy.choices, max_length=100, verbose_name='Наименование обучения',
                             db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    create = models.DateTimeField(auto_now_add=True, verbose_name='Время добавления')

    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"

    def __str__(self):
        return dict(Subject.TypeOfStudy.choices)[self.title]


class UploadFiles(models.Model):
    cat = models.ForeignKey('Departments', on_delete=models.CASCADE, related_name='wuman', verbose_name="Отделение")
    title = models.CharField(blank=True, max_length=250, db_index=True, verbose_name='Название файла')
    file = models.FileField(upload_to=get_upload_path, max_length=250)
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Время добавления')
    is_common = models.BooleanField(default=False, verbose_name='Общий файл')

    class Meta:
        verbose_name = "Файл"
        verbose_name_plural = "Файлы"
        ordering = ['-uploaded_at']

    def save(self, *args, **kwargs):
        # Устанавливаем title по умолчанию, если оно пустое
        if not self.title and self.file:
            self.title = self.file.name
        super().save(*args, **kwargs)

    def __str__(self):
        if self.cat:
            return f'{str(self.cat)} - {str(self.file.name)}'
        else:
            return f'Общий {str(self.file)}'


class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=Article.Status.PUBLISHED)


class Article(models.Model):
    class Status(models.IntegerChoices):
        DRAFT = 0, 'Черновик'
        PUBLISHED = 1, 'Опубликовано'

    title = models.CharField(max_length=255, verbose_name="Заголовок")
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name="Slug", validators=[
        MinLengthValidator(5, message="Минимум 5 символов"),
        MaxLengthValidator(100, message="Максимум 100 символов"),
    ])
    photo = models.ImageField(upload_to="photos/%Y/%m/%d/", default=None,
                              blank=True, null=True, verbose_name="Фото")
    content = RichTextField(config_name='awesome_ckeditor', blank=True, verbose_name="Текст статьи")
    time_create = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")
    time_update = models.DateTimeField(auto_now=True, verbose_name="Время изменения")
    is_published = models.BooleanField(choices=tuple(map(lambda x: (bool(x[0]), x[1]), Status.choices)),
                                       default=Status.DRAFT, verbose_name="Статус")
    category = models.ForeignKey('Categorys', on_delete=models.PROTECT, related_name='posts', verbose_name="Категории",
                                 blank=True, null=True)
    tags = models.ManyToManyField('TagPost', blank=True, related_name='tags', verbose_name="Теги")
    views = models.PositiveIntegerField(default=0)

    objects = models.Manager()
    published = PublishedManager()

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"
        ordering = ['-time_create']
        indexes = [
            models.Index(fields=['-time_create'])
        ]

    def get_absolute_url(self):
        return reverse('main:post', kwargs={'post_slug': self.slug})

    def get_sum_rating(self):
        return max(sum([rating.value for rating in self.ratings.all()]), 0)


class TagPost(models.Model):
    tag = models.CharField(max_length=100, db_index=True, verbose_name='Тэг')
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    class Meta:
        verbose_name = "Тэг"
        verbose_name_plural = "Тэги"

    def __str__(self):
        return self.tag

    def get_absolute_url(self):
        return reverse('main:tag', kwargs={'tag_slug': self.slug})


class Rating(models.Model):
    """
    Модель рейтинга: Лайк - Дизлайк
    """
    post = models.ForeignKey(Article, verbose_name='Статья', on_delete=models.CASCADE, related_name='ratings',
                             db_index=True)
    user = models.ForeignKey(get_user_model(), verbose_name='Пользователь', on_delete=models.SET_NULL, blank=True,
                             null=True)
    value = models.IntegerField(verbose_name='Значение', choices=[(1, 'Нравится'), (-1, 'Не нравится')])
    time_create = models.DateTimeField(verbose_name='Время добавления', auto_now_add=True)
    ip_address = models.GenericIPAddressField(verbose_name='IP Адрес', blank=True, null=True)

    class Meta:
        unique_together = ('post', 'user', 'ip_address')
        indexes = [models.Index(fields=['-time_create', 'value'])]
        verbose_name = 'Рейтинг'
        verbose_name_plural = 'Рейтинги'

    def __str__(self):
        if self.user:
            return f' {self.post.title} - {self.user} - {self.get_value_display()} - {self.time_create}'
        # elif not self.user:
        #     return f' {self.post.title} - Удаленный Юзер - {self.get_value_display()}'
        else:
            return f' {self.post.title} - {self.ip_address} - {self.get_value_display()} - {self.time_create}'


class Question(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions', verbose_name="Предмет")
    text = models.TextField(verbose_name="Текст вопроса")
    option1 = models.CharField(max_length=200, verbose_name="Вариант 1")
    option2 = models.CharField(max_length=200, verbose_name="Вариант 2")
    option3 = models.CharField(max_length=200, verbose_name="Вариант 3")
    option4 = models.CharField(max_length=200, verbose_name="Вариант 4")
    correct_option = models.PositiveIntegerField(verbose_name="Правильный вариант",
                                                 validators=[MinValueValidator(1), MaxValueValidator(4)])

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"

    def __str__(self):
        return f'{self.subject} - {self.text}'

    def get_absolute_url(self):
        return reverse('main:test', kwargs={'test_slug': self.subject.slug})


class Slide(models.Model):
    subject = models.ForeignKey(Subject, related_name='slides', on_delete=models.CASCADE, verbose_name='Предмет')
    content = RichTextField(config_name='awesome_ckeditor', verbose_name="Текст слайда")
    photo = models.ImageField(upload_to="courses/%Y/%m/%d/", default=None,
                              blank=True, null=True, verbose_name="Фото")
    order = models.PositiveIntegerField(verbose_name='Порядковый номер')

    class Meta:
        unique_together = ('subject', 'order')
        ordering = ['order']
        verbose_name = "Слайд"
        verbose_name_plural = "Слайды"

    def save(self, *args, **kwargs):
        # Если order не установлен, установить его на максимальное значение + 1
        if not self.order:
            max_order = Slide.objects.filter(subject=self.subject).aggregate(models.Max('order'))['order__max']
            self.order = max_order + 1 if max_order is not None else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Slide {self.order} of {self.subject.title}"

    # def get_absolute_url(self):
    #     return reverse('main:subject_detail', kwargs={'subject_slug': self.subject.slug})


class Video(models.Model):
    title = models.CharField(max_length=100, verbose_name='Название видео')
    file = models.FileField(upload_to='videos/', verbose_name='Файл')
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')

    class Meta:
        verbose_name = "Видео инструктажа"
        verbose_name_plural = "Видео"

    def __str__(self):
        return self.title


class Answer(models.Model):
    video = models.ForeignKey(Video, related_name='answers', on_delete=models.CASCADE, verbose_name='Видео')
    text = models.CharField(max_length=200, verbose_name='Текст')
    next_video = models.ForeignKey(Video, null=True, related_name='next_videos', on_delete=models.SET_NULL,
                                   verbose_name='Cледующее видео')

    class Meta:
        verbose_name = "Ответ для инструктажа"
        verbose_name_plural = "Ответы для инструктажа"

    def __str__(self):
        return f'{self.text} - {self.next_video}'

    def get_absolute_url(self):
        return reverse("main:answer", kwargs={"answer_id": self.pk})


class Comment(MPTTModel):
    """
    Модель древовидных комментариев
    """

    STATUS_OPTIONS = (
        ('published', 'Опубликовано'),
        ('draft', 'Черновик')
    )

    post = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Статья', related_name='comments',
                             db_index=True)
    user = models.ForeignKey(get_user_model(), verbose_name='Автор комментария', on_delete=models.CASCADE,
                             related_name='comments_author')
    content = models.TextField(verbose_name='Текст комментария', max_length=3000)
    time_create = models.DateTimeField(verbose_name='Время добавления', auto_now_add=True)
    time_update = models.DateTimeField(verbose_name='Время обновления', auto_now=True)
    status = models.CharField(choices=STATUS_OPTIONS, default='published', verbose_name='Статус комментария',
                              max_length=10)
    parent = TreeForeignKey('self', verbose_name='Родительский комментарий', null=True, blank=True,
                            related_name='children', on_delete=models.CASCADE)

    class MTTMeta:
        """
        Сортировка по вложенности
        """
        order_insertion_by = ('-time_create',)

    class Meta:
        """
        Сортировка, название модели в админ панели, таблица в данными
        """
        ordering = ['-time_create']
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        return f'{self.post} - {self.user}:{self.content[:20]}'
