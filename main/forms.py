from django import forms
from django.core.exceptions import ValidationError
from main.models import Categorys, UploadFiles, Article, Departments, Comment

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


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


class UploadFileForm(forms.ModelForm):
    cat = forms.ModelChoiceField(queryset=Departments.objects.all().order_by('name'), empty_label="Отделение не выбрано",
                                 label="Отделения")
    files = MultipleFileField(label="Файл")
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024

    class Meta:
        model = UploadFiles
        fields = ['cat', 'files']



    def clean_files(self):
        files = self.cleaned_data.get('files')
        if files:
            for uploaded_file in files:
                if uploaded_file.size > self.MAX_UPLOAD_SIZE:
                    raise ValidationError(f"Размер файла {uploaded_file.name} превышает максимальный размер в 10 MB.")
        return files


class SearchForm(forms.Form):
    query = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control mb-1", 'placeholder': 'Введите название документа(статьи)'}))


class CommentCreateForm(forms.ModelForm):
    """
    Форма добавления комментариев к статьям
    """
    parent = forms.IntegerField(widget=forms.HiddenInput, required=False)
    content = forms.CharField(label='', widget=forms.Textarea(
        attrs={'cols': 30, 'rows': 5, 'placeholder': 'Комментарий', 'class': 'form-control'}))

    class Meta:
        model = Comment
        fields = ('content',)
