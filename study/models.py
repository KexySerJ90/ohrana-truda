from ckeditor.fields import RichTextField
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords


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
        return reverse('study:test', kwargs={'test_slug': self.subject.slug})



class Slide(models.Model):
    subject = models.ForeignKey(Subject, related_name='slides', on_delete=models.CASCADE, verbose_name='Предмет')
    content = RichTextField(config_name='awesome_ckeditor', verbose_name="Текст слайда")
    photo = models.ImageField(upload_to="courses/%Y/%m/%d/", default=None,
                              blank=True, null=True, verbose_name="Фото")
    order = models.PositiveIntegerField(verbose_name='Порядковый номер', blank=True)

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
    #     return reverse('study:subject_detail', kwargs={'subject_slug': self.subject.slug})


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
        return reverse("study:answer", kwargs={"answer_id": self.pk})



class SubjectCompletion(models.Model):
    users = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='subject_completions', verbose_name="Пользователь")
    subjects = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name='subject_completions', verbose_name="Предмет")
    completed = models.BooleanField(default=False, verbose_name="Тестирование")
    score= models.PositiveIntegerField(default=0, verbose_name='Количество баллов')
    study_completed=models.BooleanField(default=False, verbose_name="Обучение")
    current_slide = models.ForeignKey('Slide', on_delete=models.SET_NULL, null=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('users', 'subjects')
        verbose_name = "Экзамен"
        verbose_name_plural = "Экзамены"


    def __str__(self):
        return f'{self.users.last_name} {str(self.users.first_name)} - {str(self.subjects)}'


class UserAnswer(models.Model):
    user_completion = models.ForeignKey('study.SubjectCompletion', on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey('study.Question', on_delete=models.CASCADE, related_name='user_answers')
    selected_answer = models.PositiveIntegerField(verbose_name='Выбранный ответ', null=True)

    class Meta:
        verbose_name = "Ответ пользователя"
        verbose_name_plural = "Ответы пользователей"

    def __str__(self):
        return f'{self.user_completion} - {self.question.text}'