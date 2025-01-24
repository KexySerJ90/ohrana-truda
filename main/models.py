from ckeditor.fields import RichTextField
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.db import models
from django.urls import reverse
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from simple_history.models import HistoricalRecords
from main.utils import get_upload_path
from users.models import Profession


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

class UploadFiles(models.Model):
    cat = models.ForeignKey('Departments', on_delete=models.CASCADE, related_name='wuman', verbose_name="Отделение")
    title = models.CharField(blank=True, max_length=500, db_index=True, verbose_name='Название файла')
    file = models.FileField(upload_to=get_upload_path, max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Время добавления')
    is_common = models.BooleanField(default=False, verbose_name='Общий файл')
    description = models.TextField(max_length=900, verbose_name='Описание', default='',blank=True, null=True)

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
    views=models.PositiveIntegerField(default=0,verbose_name='Просмотры')
    history = HistoricalRecords()

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

class UniqueView(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='unique_views', verbose_name='Статья')
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True,verbose_name='Дата просмотра')
    class Meta:
        verbose_name = "Уникальный просмотр"
        verbose_name_plural = "Уникальные просмотры"
        unique_together = ('article', 'ip_address')

    def __str__(self):
        return f'{self.article}-{self.ip_address}'


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


class Equipment(models.Model):
    name = models.CharField(max_length=350,verbose_name='Название средств индивидуальной защиты', unique=True)
    description=models.CharField(max_length=500,verbose_name='Описание СИЗ')
    quantity = models.CharField(default='1', verbose_name='Количество')
    basis=models.CharField(max_length=500, verbose_name='Основание', null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "СИЗ"
        verbose_name_plural = "СИЗ"

class WorkingConditions(models.Model):
    name = models.CharField(max_length=250, verbose_name='Класс условий труда', unique=True, db_index=True)
    description=models.CharField(max_length=250, verbose_name='Описание', blank=True, null=True)
    money=models.PositiveIntegerField(verbose_name='Повышенная оплата труда,%',blank=True, null=True)
    weekend=models.PositiveIntegerField(verbose_name='Дополнительный отпуск,количество дней',blank=True, null=True)
    duration = models.BooleanField(verbose_name='Сокращенная продолжительность рабочего времени, да/нет')
    milk = models.BooleanField(verbose_name='Молоко, да/нет')
    food=models.BooleanField(verbose_name='Лечебно-профилактическое питание, да/нет')
    pension=models.BooleanField(verbose_name='Льготное пенсионное обеспечение, да/нет')
    medical = models.BooleanField(verbose_name='Проведение медицинских осмотров, да/нет')

    class Meta:
        verbose_name = 'Условия труда'
        verbose_name_plural = 'Условия труда'

    def __str__(self):
        return self.name

class JobDetails(models.Model):
    class OPR(models.TextChoices):
        LOW=('low', 'Низкий')
        MODERATE=('moderate', 'Умеренный')
        MEDIUM=('medium', 'Средний')
        SIGNIFICANT = ('significant', 'Значительный')
        HIGH = ('high', 'Высокий')
    profession = models.ForeignKey(Profession, on_delete=models.CASCADE, verbose_name='Должность')
    department = models.ForeignKey('main.Departments', on_delete=models.CASCADE, verbose_name='Отделение')
    working_conditions = models.ForeignKey(WorkingConditions, on_delete=models.CASCADE, verbose_name='Условия труда', null=True, blank=True)
    date_of_sout=models.DateField(verbose_name='Дата СОУТ',blank=True,null=True)
    opr = models.CharField(choices=OPR.choices, max_length=100, verbose_name='Уровень риска', blank=True, null=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('profession', 'department')
        verbose_name = 'Рабочее место'
        verbose_name_plural = 'Рабочие места'

    def __str__(self):
        return f'{self.department}-{self.profession}'