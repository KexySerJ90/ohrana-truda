import os
import re

import markdown
from django.db.models import Count, Q, F
from django.template.defaultfilters import stringfilter
from django import template
from django.utils.safestring import mark_safe
from main.models import Categorys, TagPost, Article

register = template.Library()


@register.simple_tag()
def tag_categories():
    return Categorys.objects.all()



@register.filter
@stringfilter
def cuter(value):
    """
    Обрезает строку, оставляя только имя файла и убирая его расширение.
    Результат возвращается с заглавной буквы и без латинских символов.

    :param value: Строка, содержащая путь к файлу.
    :return: Имя файла с заглавной буквы без латинских символов.

    Пример использования:
    {{ 'path/to/file.txt' | cuter }}  -> 'Файл' (если имя файла содержит кириллицу)
    """
    # Извлекаем имя файла без расширения
    filename = '.'.join(value.split("/")[-1].split(".")[:-1])

    # Удаляем латинские символы с помощью регулярного выражения
    filtered_filename = ' '.join(re.sub(r'[a-zA-Z]', '', filename).split('_'))

    # Возвращаем результат с заглавной буквы
    return filtered_filename.capitalize()


@register.filter
def format_views(value):
    """
    Форматирует количество просмотров. Если количество просмотров
    больше или равно 1,000, то оно отображается в формате "Xk",
    где X - количество тысяч. Если больше или равно 1,000,000,
    возвращает '>9k'.

    Пример использования:
    {{ 1500 | format_views }}  -> '1k'
    {{ 5000000 | format_views }}  -> '>9k'
    """
    if value >= 1000000:
        return '>9k'
    elif value >= 1000:
        return f'{value // 1000}k'
    return value


@register.inclusion_tag('main/list_categories.html')
def show_categories(cat_selected=0):
    """
    Отображает список категорий с количеством связанных постов.

    :param cat_selected: ID выбранной категории (по умолчанию 0).
    :return: Словарь с категориями и ID выбранной категории.

    Пример использования:
    {% show_categories cat_selected=selected_category_id %}
    """
    cats = Categorys.objects.annotate(total=Count("posts")).filter(total__gt=0)
    return {'cats': cats, 'cat_selected': cat_selected}


@register.inclusion_tag('main/list_tags.html')
def show_all_tags():
    """
    Отображает случайные теги, у которых есть связанные посты.

    :return: Словарь с тремя случайными тегами.

    Пример использования:
    {% show_all_tags %}
    """
    return {'tags': TagPost.objects.annotate(total=Count("tags")).filter(total__gt=0).order_by('?')[:3]}


@register.inclusion_tag('main/latest_posts.html')
def show_popular_posts(count):
    """
    Отображает популярные посты, отсортированные по чистому рейтингу
    (разница между лайками и дизлайками).

    :param count: Количество популярных постов для отображения.
    :return: Словарь с популярными постами.

    Пример использования:
    {% show_popular_posts 5 %}
    """
    popular_posts = Article.published.annotate(
        total_likes=Count('ratings', filter=Q(ratings__value=1)),
        total_dislikes=Count('ratings', filter=Q(ratings__value=-1)),
        net_rating=F('total_likes') - F('total_dislikes')
    ).order_by('-net_rating')[:count]
    return {'popular_posts': popular_posts}


@register.inclusion_tag('main/comment_posts.html')
def articles_by_comment_count(count):
    """
    Отображает статьи, отсортированные по количеству комментариев.

    :param count: Количество статей для отображения.
    :return: Словарь с статьями, отсортированными по количеству комментариев.

    Пример использования:
    {% articles_by_comment_count 5 %}
    """
    comment_posts = Article.objects.annotate(comment_count=Count('comments')).order_by('-comment_count')[:count]
    return {'comment_posts': comment_posts}

@register.filter(name='markdown')
def markdown_format(text):
    return mark_safe(markdown.markdown(text))


@register.filter
def pluralize_ru(value, arg):
    """
    Функция для правильного склонения существительных в русском языке.
    Пример использования: {{ count|pluralize_ru:"файл,файла,файлов" }}
    """
    value = int(value)
    if value % 10 == 1 and value % 100 != 11:
        return arg.split(',')[0]  # ед. число
    elif 2 <= value % 10 <= 4 and not (12 <= value % 100 <= 14):
        return arg.split(',')[1]  # род. число
    else:
        return arg.split(',')[2]

@register.filter
def file_icon(file_path):
    _, extension = os.path.splitext(file_path)
    if extension.lower() == '.pdf':
        return '<i class="fas fa-file-pdf me-2"></i>'
    elif extension.lower() == '.doc' or extension.lower() == '.docx':
        return '<i class="fas fa-file-word me-2"></i>'
    else:
        return '<i class="fas fa-file me-2"></i>'  # Универсальная иконка для других типов файлов


@register.filter
def div_size(size):
    return round(size / 1048576,1)
