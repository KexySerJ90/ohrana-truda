from datetime import datetime
from django.utils import timezone
from typing import Dict, Any

def get_upload_path(instance, filename: str) -> str:
    """ Определяет путь для загрузки файла в зависимости от категории и других параметров объекта. :param instance: Экземпляр модели, для которого определяется путь загрузки. :param filename: Имя загружаемого файла. :return: Строка с полным путем для сохранения файла. """
    if instance.cat and instance.cat.slug == 'sout':
        # Если категория объекта равна 'sout', сохраняем файл в специальную папку
        return f'uploads_model/sout/{filename}'
    elif instance.cat:
        if instance.is_common:
            # Если объект общий, сохраняем в общую папку с текущей датой
            return f'uploads_model/general/common/{timezone.now().strftime("%Y-%m-%d")}/{filename}'
    # В остальных случаях сохраняем в папку соответствующей категории с текущей датой
    return f'uploads_model/general/{instance.cat.name}/{timezone.now().strftime("%Y-%m-%d")}/{filename}'


class DataMixin:
    """ Миксин для добавления общих свойств и методов в другие классы. """
    paginate_by = 4  # Количество объектов на странице при пагинации
    title_page = None  # Заголовок страницы
    cat_selected = None  # Выбранная категория
    extra_context = {}  # Дополнительный контекст для передачи в шаблон

    def __init__(self) -> None:
        if self.title_page:
            self.extra_context['title'] = self.title_page
        if self.cat_selected is not None:
            self.extra_context['cat_selected'] = self.cat_selected

    def get_mixin_context(self, context: dict, **kwargs: any) -> dict:
        """ Обновление контекста перед передачей его в шаблон. :param context: Исходный контекст. :param kwargs: Дополнительные аргументы. :return: Обновленный контекст. """
        context['cat_selected'] = None
        context.update(kwargs)
        return context


def Leap_years(years_to_subtract: int = 16) -> int:
    """ Подсчитывает количество високосных лет за последние N лет до текущего года. :param years_to_subtract: Количество лет назад, начиная с которых считать високосные годы. По умолчанию равно 16. :return: Количество високосных лет. """
    current_date = datetime.now()
    return sum([
        1 for year in range(current_date.year - years_to_subtract, current_date.year)
        if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    ])

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    return ip_address
