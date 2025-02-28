from django import forms
from django.core.exceptions import ValidationError
from emoji_picker.widgets import EmojiPickerTextareaAdmin

from main.models import Categorys, UploadFiles, Article, Comment
from main.utils import validate_file
from users.models import Departments

from users.utils import COMMON_TEXT_INPUT_ATTRS, CustomEmailWidget


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput()

    def to_python(self, data):
        if hasattr(data, '__iter__') and not isinstance(data, str):
            return list(super(MultipleFileField, self).to_python(item) for item in data)
        return super().to_python(data)

    def validate(self, value):
        super().validate(value)
        for v in value:
            validate_file(v)

class UploadFileForm(forms.ModelForm):
    cat = forms.ModelChoiceField(queryset=Departments.objects.all().order_by('name'), empty_label="Отделение не выбрано",
                                 label="Отделения")
    files = MultipleFileField(label="Файл")


    class Meta:
        model = UploadFiles
        fields = ['cat', 'files']


class AddPostForm(forms.ModelForm):
    cat3 = forms.ModelChoiceField(queryset=Categorys.objects.all(), empty_label="Категория не выбрана",
                                  label="Категории")

    class Meta:
        model = Article
        fields = ['title', 'slug', 'content', 'photo', 'is_published', 'cat3', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'content': forms.Textarea(attrs={'cols': 50, 'rows': 5}),
        }
        labels = {'slug': 'URL'}

    def clean_title(self):
        title = self.cleaned_data['title']
        if len(title) > 60:
            raise ValidationError("Длина превышает 60 символов")
        return title

class SearchForm(forms.Form):
    query = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control mb-1", 'placeholder': 'Введите название документа(статьи)'}))


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

