from django import forms

from users.models import Profession
from users.utils import ProfessionChoiceField


class ProfessionForm(forms.ModelForm):
    name = ProfessionChoiceField(label="Профессия", empty_label='Выберите профессию')

    class Meta:
        model = Profession
        fields = ['name']