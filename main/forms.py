from django import forms
from django.core.exceptions import ValidationError
from emoji_picker.widgets import EmojiPickerTextareaAdmin

from main.models import Categorys, UploadFiles, Article, Comment
from main.utils import validate_file
from users.models import Departments

from users.utils import COMMON_TEXT_INPUT_ATTRS, CustomEmailWidget


class MultipleFileInput(forms.ClearableFileInput):
    # Класс для создания виджета ввода нескольких файлов, который позволяет очищать выбор файла.
    allow_multiple_selected = True  # Позволяет выбрать несколько файлов одновременно.


class MultipleFileField(forms.FileField):
    # Поле формы для загрузки нескольких файлов.
    widget = MultipleFileInput()  # Использует созданный выше виджет для ввода файлов.

    def clean(self, data, initial=None):
        if data is None:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        result = []
        for item in data:
            super().clean(item, initial)
            validate_file(item)
            result.append(item)
        return result
    # def to_python(self, data):
    #     # Преобразует входные данные в список загруженных файлов.
    #     if hasattr(data, 'iter') and not isinstance(data, str):
    #         return list(super(MultipleFileField, self).to_python(item) for item in data)  # Преобразует каждый файл в объект.
    #     return super().to_python(data)  # Для одиночного файла вызывает родительский метод.
    #
    # def validate(self, value):
    #     # Проверяет валидность загруженных файлов.
    #     super().validate(value)  # Вызывает стандартную проверку валидности.
    #     for v in value:
    #         validate_file(v)  # Проверяет каждый файл на соответствие заданным условиям.


class UploadFileForm(forms.ModelForm):
    # Форма для загрузки файлов с выбором отделения.
    cat = forms.ModelChoiceField(queryset=Departments.objects.all().order_by('name'), empty_label="Отделение не выбрано",
                                 label="Отделения")  # Поле для выбора отделения из базы данных.
    files = MultipleFileField(label="Файл")  # Поле для загрузки нескольких файлов.

    class Meta:
        model = UploadFiles  # Связывает форму с моделью UploadFiles.
        fields = ['cat', 'files']  # Указывает поля, которые будут включены в форму.


class AddPostForm(forms.ModelForm):
    # Форма для добавления новой статьи.
    cat3 = forms.ModelChoiceField(queryset=Categorys.objects.all(), empty_label="Категория не выбрана",
                                  label="Категории")  # Поле для выбора категории статьи.

    class Meta:
        model = Article  # Связывает форму с моделью Article.
        fields = ['title', 'slug', 'content', 'photo', 'is_published', 'cat3', 'tags']  # Указывает поля для формы.
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),  # Настраивает виджет для ввода заголовка.
            'content': forms.Textarea(attrs={'cols': 50, 'rows': 5}),  # Настраивает виджет для ввода содержания статьи.
        }
        labels = {'slug': 'URL'}  # Задает пользовательскую метку для поля slug.

    def clean_title(self):
        # Метод для проверки заголовка статьи на соответствие длине.
        title = self.cleaned_data['title']  # Получает заголовок из очищенных данных.
        if len(title) > 60:  # Проверяет длину заголовка.
            raise ValidationError("Длина превышает 60 символов")  # Вызывает ошибку, если длина превышает допустимую.
        return title  # Возвращает корректный заголовок.


class SearchForm(forms.Form):
    # Форма для поиска статей по запросу.
    query = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control mb-1", 'placeholder': 'Введите название документа(статьи)'}))  # Поле для ввода поискового запроса с заданными атрибутами стиля.
class CommentCreateForm(forms.ModelForm):
    """
    Форма добавления комментариев к статьям
    """
    parent = forms.IntegerField(widget=forms.HiddenInput, required=False)
    content = forms.CharField(label='', widget=EmojiPickerTextareaAdmin(
        attrs={'cols': 90, 'rows': 5, 'placeholder': 'Комментарий', 'class': 'form-control'}))
    image = forms.ImageField(required=False, widget=forms.HiddenInput)


    class Meta:
        model = Comment
        fields = ('content',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].disabled = True




class ContactForm(forms.Form):
    username = forms.CharField(max_length=100, label="Логин", widget=forms.TextInput(attrs={
        **COMMON_TEXT_INPUT_ATTRS,
        'readonly': 'readonly',
        'style': 'background-color: #dee2e6;'}))
    email = forms.EmailField(widget=CustomEmailWidget())
    message = forms.CharField(label="Сообщение", widget=forms.Textarea(attrs=COMMON_TEXT_INPUT_ATTRS))

