from django import forms
from .models import SubjectCompletion

class SubjectCompletionForm(forms.ModelForm):
    class Meta:
        model = SubjectCompletion
        fields = ['subjects']