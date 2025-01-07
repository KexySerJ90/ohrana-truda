from datetime import datetime
from django.utils import timezone
from typing import Dict, Any

def get_upload_path(instance, filename:str) ->str:
    if instance.cat and instance.cat.slug=='sout':
        return f'uploads_model/sout/{filename}'
    elif instance.cat:
        if instance.is_common:
            return f'uploads_model/general/common/{timezone.now().strftime("%Y-%m-%d")}/{filename}'
    return f'uploads_model/general/{instance.cat.name}/{timezone.now().strftime("%Y-%m-%d")}/{filename}'


class DataMixin:
    paginate_by = 4
    title_page = None
    cat_selected = None
    extra_context = {}

    def __init__(self) -> None:
        if self.title_page:
            self.extra_context['title'] = self.title_page
        if self.cat_selected is not None:
            self.extra_context['cat_selected'] = self.cat_selected

    def get_mixin_context(self, context: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        context['cat_selected'] = None
        context.update(kwargs)
        return context

def Leap_years(years_to_subtract:int = 16) ->int:
    current_date = datetime.now()
    return sum([1 for year in range(current_date.year - years_to_subtract, current_date.year) if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0])