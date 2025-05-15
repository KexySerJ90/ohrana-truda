from itertools import chain
from typing import Any, Dict, List, Optional
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse
import locale
from django.utils import timezone
from babel.dates import format_datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.contrib.postgres.search import TrigramSimilarity, TrigramWordSimilarity
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.http import require_safe
from django.views.generic import FormView, CreateView, ListView, DetailView, UpdateView, DeleteView
from main.forms import UploadFileForm, SearchForm, AddPostForm, CommentCreateForm, ContactForm
from main.models import UploadFiles, Article, TagPost, Rating, Comment, UniqueView, \
    Notification, Notice, UserLoginHistory, SentMessage
from main.permissions import AuthorPermissionsMixin
from main.utils import DataMixin, get_client_ip
from ohr.settings import EMAIL_HOST_USER, EMAIL_RECIPIENT_LIST, DEFAULT_USER_IMAGE
from users.models import Departments
from users.permissions import StatusRequiredMixin


class IndexView(ListView):
    """Определяем класс представления для главной страницы"""
    queryset = Article.published  # Получаем опубликованные статьи
    template_name = 'main/index.html'  # Указываем шаблон для отображения

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        # Получаем контекст для шаблона
        context = super().get_context_data(**kwargs)
        context['title'] = 'Home - Охрана труда'  # Заголовок страницы
        context['content'] = "Охрана труда"  # Основное содержание страницы
        context['arts'] = Article.published.all()[:3]  # Получаем три последние опубликованные статьи

        return context


@require_safe
def about(request: HttpRequest) -> HttpResponse:
    # Представление для страницы "О нас"
    return render(request, 'main/about.html', context={
        'title': 'Home - О нас',  # Заголовок страницы
    })

@require_safe
def consent(request: HttpRequest) -> HttpResponse:
    # Представление для страницы "О нас"
    return render(request, 'main/consent.html', context={
        'title': 'Согласие на обработку персональных данных',  # Заголовок страницы
    })


class UploadFileView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Представление для загрузки файлов, требует аутентификации и проверки прав доступа"""
    template_name = 'main/addfile.html'  # Шаблон для формы загрузки
    form_class = UploadFileForm  # Форма для загрузки файлов
    success_url = reverse_lazy('main:add_file')  # URL для перенаправления после успешной загрузки

    def form_valid(self, form):
        # Обработка валидной формы
        category = form.cleaned_data['cat']  # Получаем выбранную категорию из формы
        files: List[Any] = self.request.FILES.getlist('files')  # Получаем загруженные файлы
        is_common: bool = category.is_inpatient  # Проверяем, является ли категория стационарной
        departments = Departments.objects.filter(is_inpatient=is_common)  # Получаем отделения по критерию

        if is_common:
            # Если категория стационарная, создаем общие записи для каждого файла
            common_uploads = []
            for uploaded_file in files:
                common_upload = UploadFiles.objects.create(
                    cat=departments.first(),  # Берем первое отделение для создания общей записи
                    file=uploaded_file,
                    is_common=True
                )
                common_uploads.append(common_upload)

            # Копируем общие записи для остальных отделений
            for common_upload in common_uploads:
                for department in departments.exclude(pk=common_upload.cat.pk):
                    UploadFiles.objects.create(
                        cat=department,
                        file=common_upload.file,
                        is_common=True
                    )
        else:
            # Если категория не стационарная, создаем записи только для выбранной категории
            for uploaded_file in files:
                UploadFiles.objects.create(file=uploaded_file, cat=category, is_common=False)

        return super().form_valid(form)  # Возвращаем результат обработки формы

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        # Получаем контекст для шаблона загрузки файлов
        context = super().get_context_data(**kwargs)
        context['files'] = UploadFiles.objects.all()  # Передаем все загруженные файлы в контекст
        return context

    def test_func(self) -> bool:
        # Проверка прав доступа: пользователь должен быть администратором или суперпользователем
        return self.request.user.is_staff or self.request.user.is_superuser


class Mainfiles(LoginRequiredMixin, StatusRequiredMixin, AuthorPermissionsMixin, ListView):
    """Представление для отображения загруженных файлов в зависимости от категории"""
    template_name = 'main/mainfiles.html'  # Шаблон для отображения файлов
    context_object_name = 'posts'  # Имя контекстного объекта для шаблона
    paginate_by = 6  # Количество файлов на странице

    def get_queryset(self):
        # Получаем набор данных файлов в зависимости от прав доступа и параметров сортировки
        if self.has_permissions():
            queryset = UploadFiles.objects.filter(cat__slug=self.kwargs['dep_slug'])  # Фильтруем по slug категории
            order_by = self.request.GET.get('order_by', '')  # Получаем параметр сортировки из запроса

            # Применяем сортировку по выбранному критерию
            if order_by == 'title':
                queryset = queryset.order_by('title')
            elif order_by == '-title':
                queryset = queryset.order_by('-title')
            elif order_by == 'uploaded_at':
                queryset = queryset.order_by('uploaded_at')
            elif order_by == '-uploaded_at':
                queryset = queryset.order_by('-uploaded_at')

            return queryset  # Возвращаем отсортированный набор данных
        raise PermissionDenied  # Если нет прав доступа, выбрасываем исключение

    def get_context_data(self, **kwargs):
        # Получаем контекст для шаблона отображения файлов
        context = super().get_context_data(**kwargs)
        department = Departments.objects.get(slug=self.kwargs['dep_slug'])  # Получаем отделение по slug из URL
        context['title'] = f'Файлы - {department.name}'  # Устанавливаем заголовок страницы с названием отделения
        return context


class ArticlePosts(DataMixin, ListView):
    """ Представление для отображения статей"""
    template_name = 'main/posts.html'  # Шаблон для отображения списка статей
    context_object_name = 'posts'  # Имя контекстной переменной для списка статей
    title_page = 'Статьи'  # Заголовок страницы
    cat_selected = 0  # Выбранная категория (по умолчанию 0)

    def get_queryset(self):
        # Получаем список опубликованных статей с предварительной выборкой связанных данных
        return Article.published.select_related('category').prefetch_related('ratings')


class AddPostView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """ Представление для добавление статьи"""
    form_class = AddPostForm  # Форма для добавления новой статьи
    template_name = 'main/addpage.html'  # Шаблон для страницы добавления статьи
    extra_context = {'title': 'Добавление статьи'}  # Дополнительный контекст для заголовка страницы

    def test_func(self) -> bool:
        # Проверка, имеет ли пользователь право на добавление статьи
        return self.request.user.is_staff or self.request.user.is_superuser


class ShowPost(DataMixin, DetailView):
    """ Представление для отображения конкретной статьи"""
    template_name = 'main/post.html'  # Шаблон для отображения отдельной статьи
    slug_url_kwarg = 'post_slug'  # Параметр URL для получения слага статьи
    context_object_name = 'post'  # Имя контекстной переменной для статьи

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)  # Получаем базовый контекст
        post = context['post']  # Получаем статью из контекста
        context['form'] = CommentCreateForm  # Добавляем форму для комментариев в контекст
        return self.get_mixin_context(context, title=post.title)  # Добавляем заголовок статьи в контекст

    def get_object(self, queryset=None) -> Article:
        # Получаем объект статьи по слагу из URL
        article = get_object_or_404(Article.published.prefetch_related('comments__user__profile'),
                                    slug=self.kwargs[self.slug_url_kwarg])
        ip_address = get_client_ip(self.request)  # Получаем IP-адрес пользователя
        if not UniqueView.objects.filter(article=article, ip_address=ip_address).exists():
            # Если запись о уникальном просмотре отсутствует, создаем ее
            UniqueView.objects.create(article=article, ip_address=ip_address)

            # Увеличиваем количество уникальных просмотров
        article.views = article.unique_views.count()  # Обновляем общее количество просмотров
        article.save(update_fields=['views'])  # Сохраняем только поле views
        # Увеличиваем количество просмотров
        return article


class UpdatePage(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """ Представление для редактирования статьи"""
    model = Article  # Модель, которую мы будем обновлять
    fields = ['title', 'content', 'photo', 'is_published', 'category', 'tags']  # Поля для редактирования
    template_name = 'main/addpage.html'  # Шаблон для страницы редактирования статьи
    success_url = reverse_lazy('main:home')  # URL для перенаправления после успешного обновления
    extra_context = {'title': 'Редактирование статьи'}  # Дополнительный контекст для заголовка страницы
    permission_required = 'main.change_article'  # Разрешение, необходимое для редактирования статьи


class ArticleCategory(DataMixin, ListView):
    """ Представление для отображения статей по категориям"""
    template_name = 'main/posts.html'  # Шаблон для отображения списка статей по категории
    context_object_name = 'posts'  # Имя контекстной переменной для списка статей
    allow_empty = False  # Запрет на пустые результаты

    def get_queryset(self):
        # Получаем список опубликованных статей по выбранной категории
        return Article.published.filter(category__slug=self.kwargs['cat_slug']).select_related("category")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)  # Получаем базовый контекст
        if context['posts']:
            cat = context['posts'][0].category  # Получаем категорию из первой статьи в списке
            context = self.get_mixin_context(context,
                                             title='Категория - ' + cat.name,
                                             # Заголовок страницы с названием категории
                                             cat_selected=cat.pk)  # Выбранная категория для отображения в навигации
            return context


class TagPostList(DataMixin, ListView):
    """ Представление для отображения статей по тэгам"""
    template_name = 'main/posts.html'  # Шаблон для отображения списка постов
    context_object_name = 'posts'  # Имя контекста для списка постов
    allow_empty = False  # Запрещаем пустые результаты

    def get_context_data(self, *, object_list: Optional[List[Article]] = None, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)  # Получаем базовый контекст
        tag = TagPost.objects.get(slug=self.kwargs['tag_slug'])  # Получаем тег по slug
        return self.get_mixin_context(context, title='Тег: ' + tag.tag)  # Добавляем заголовок с тегом

    def get_queryset(self):
        # Получаем список опубликованных статей с определенным тегом
        return Article.published.filter(tags__slug=self.kwargs['tag_slug']).select_related('category')


class RatingCreateView(View):
    """ Представление для создание лайков"""
    model = Rating  # Определяем модель рейтинга

    def post(self, request, *args, **kwargs):
        post_id = request.POST.get('post_id')  # Получаем ID поста из POST-запроса
        value = int(request.POST.get('value'))  # Получаем значение рейтинга
        ip_address = get_client_ip(request)  # Получаем IP-адрес пользователя
        user = request.user if request.user.is_authenticated else None  # Определяем пользователя (авторизованный или нет)

        # Для неавторизованных пользователей:
        if user is None:
            rating_queryset = self.model.objects.filter(post_id=post_id, ip_address=ip_address, user=None)
        else:  # Для авторизованных пользователей:
            rating_queryset = self.model.objects.filter(post_id=post_id, user=user)

        if rating_queryset.exists():  # Если рейтинг уже существует
            rating = rating_queryset.first()  # Получаем первый найденный рейтинг
            if rating.value == value:  # Если значение рейтинга совпадает с текущим
                rating.delete()  # Удаляем рейтинг
                return JsonResponse({'status': 'deleted',
                                     'rating_sum': rating.post.get_sum_rating()})  # Возвращаем статус удаления и сумму рейтинга
            else:
                rating.value = value  # Обновляем значение рейтинга
                if user is None:  # Обновляем ip_address только для неавторизованных пользователей
                    rating.ip_address = ip_address
                rating.save()  # Сохраняем изменения в рейтинге
                return JsonResponse({'status': 'updated',
                                     'rating_sum': rating.post.get_sum_rating()})  # Возвращаем статус обновления и сумму рейтинга
        else:
            # Создаем новый рейтинг, если он не существует
            rating = self.model.objects.create(
                post_id=post_id,
                user=user,
                ip_address=ip_address,
                value=value,
            )
            return JsonResponse({'status': 'created',
                                 'rating_sum': rating.post.get_sum_rating()})  # Возвращаем статус создания и сумму рейтинга


class CommentCreateView(LoginRequiredMixin, CreateView):
    """ Представление для создания комментариев"""
    model = Comment  # Указываем модель, с которой будет работать представление (в данном случае - комментарии).
    form_class = CommentCreateForm  # Указываем форму для создания комментариев.

    def is_ajax(self) -> bool:
        # Метод для проверки, является ли запрос AJAX-запросом.
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def form_invalid(self, form: CommentCreateForm) -> JsonResponse:
        # Переопределяем метод для обработки случая, когда форма недействительна.
        if self.is_ajax():
            # Если запрос AJAX, возвращаем ошибки формы в формате JSON.
            return JsonResponse({'error': form.errors}, status=400)
        # В противном случае вызываем стандартную обработку недействительной формы.
        return super().form_invalid(form)

    def form_valid(self, form: CommentCreateForm) -> JsonResponse:
        # Переопределяем метод для обработки случая, когда форма действительна.
        locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')  # Устанавливаем локаль для корректного отображения времени.
        comment = form.save(commit=False)  # Создаем объект комментария, но не сохраняем его в базе данных сразу.
        comment.post_id = self.kwargs.get('pk')  # Устанавливаем идентификатор поста, к которому относится комментарий.
        comment.user = self.request.user  # Устанавливаем текущего пользователя как автора комментария.
        comment.parent_id = form.cleaned_data.get(
            'parent')  # Получаем идентификатор родительского комментария (если есть).
        comment.save()  # Сохраняем комментарий в базе данных.

        # Если в запросе есть изображение, сохраняем его вместе с комментарием.
        if 'image' in self.request.FILES:
            image_file = self.request.FILES['image']
            comment.image.save(image_file.name, image_file)

        parent_comment_id = comment.parent_id  # Получаем идентификатор родительского комментария.
        if parent_comment_id:
            parent_comment = get_object_or_404(Comment,
                                               id=parent_comment_id)  # Получаем родительский комментарий или 404, если не найден.
            if parent_comment.user != comment.user:  # Проверяем, что автор родительского комментария не совпадает с автором нового комментария.
                Notification.objects.create(user=parent_comment.user,
                                            comment=comment)  # Создаем уведомление для автора родительского комментария.

        if self.is_ajax():
            # Если запрос AJAX, возвращаем данные о новом комментарии в формате JSON.
            return JsonResponse({
                'is_child': comment.is_child_node(),  # Указываем, является ли комментарий дочерним.
                'id': comment.id,  # Возвращаем идентификатор комментария.
                'author': comment.user.username,  # Имя автора комментария.
                'parent_id': comment.parent_id,  # Идентификатор родительского комментария.
                'time_create': format_datetime(comment.time_create, format='dd MMMM yyyy г. HH:mm', locale='ru'),
                # Форматируем время создания комментария.
                'photo': comment.user.profile.photo.url if comment.user.profile.photo else DEFAULT_USER_IMAGE,
                # URL фотографии автора или изображение по умолчанию.
                'content': comment.content,  # Содержимое комментария.
            }, status=200)

        return redirect(comment.post.get_absolute_url())  # В противном случае перенаправляем на страницу поста.

    def handle_no_permission(self) -> JsonResponse:
        # Обработка случая, когда пользователь не авторизован.
        return JsonResponse({'error': 'Необходимо авторизоваться для добавления комментариев'}, status=400)


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    """ Представление для удаления комментариев"""
    model = Comment  # Указываем модель для удаления (в данном случае - комментарии).

    def is_ajax(self) -> bool:
        # Метод для проверки, является ли запрос AJAX-запросом.
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        # Переопределяем метод удаления комментария.
        comment = get_object_or_404(Comment, pk=kwargs['pk'],
                                    user=request.user)  # Получаем комментарий по идентификатору и проверяем, что он принадлежит текущему пользователю.
        comment.delete()  # Удаляем комментарий из базы данных.

        if self.is_ajax():
            # Если запрос AJAX, возвращаем успешный ответ в формате JSON.
            return JsonResponse({'success': True}, status=200)

        return redirect(comment.post.get_absolute_url())  # В противном случае перенаправляем на страницу поста.

    def handle_no_permission(self) -> JsonResponse:
        # Обработка случая, когда пользователь не авторизован.
        return JsonResponse({'error': 'Необходимо авторизоваться для удаления комментариев'}, status=403)


class PostSearchView(View):
    """ Представление для поиска статей и файлов"""
    form_class = SearchForm  # Определяем класс формы для поиска
    template_name = 'main/search.html'  # Шаблон для отображения результатов поиска

    def get(self, request, *args, **kwargs):
        form = self.form_class()  # Создаем пустую форму
        query = None  # Инициализируем переменную для запроса
        results_files = []  # Список для хранения результатов поиска файлов
        results_articles = []  # Список для хранения результатов поиска статей

        # Проверяем, есть ли параметр 'query' в GET-запросе
        if 'query' in request.GET:
            form = self.form_class(request.GET)  # Заполняем форму данными из запроса
            if form.is_valid():  # Проверяем, является ли форма валидной
                A = 1.0  # Вес для заголовка статьи
                B = 0.4  # Вес для содержимого статьи
                query = form.cleaned_data['query']  # Получаем очищенные данные из формы

                # Поиск файлов с использованием триграммного сходства
                results_files = UploadFiles.objects.annotate(
                    similarity=TrigramSimilarity('file', query),
                ).filter(similarity__gt=0.07).order_by('title', '-similarity').distinct('title')

                # Поиск статей с использованием взвешенного триграммного сходства
                results_articles = Article.objects.annotate(
                    similarity=(A / (A + B) * TrigramSimilarity('title', query)
                                + B / (A + B) * TrigramWordSimilarity(query, 'content'))
                ).filter(similarity__gt=0.25).order_by('-similarity')

        # Подготавливаем контекст для рендеринга шаблона
        context = {
            'form': form,
            'query': query,
            'results_files': results_files,
            'results_articles': results_articles,
            'articles': Article.published.all()  # Получаем все опубликованные статьи
        }
        return render(request, self.template_name, context)  # Возвращаем отрендеренный шаблон

        # search_vector = SearchVector('title', weight='A') + \
        #                 SearchVector('body', weight='B')
        # search_query = SearchQuery(query)
        # results = Post.published.annotate(
        #     search=search_vector,
        #     rank=SearchRank(search_vector, search_query)
        # ).filter(search=search_query).order_by('-rank')


class NotificationListView(LoginRequiredMixin, ListView):
    """ Представление для отображения уведомлений"""
    extra_context = {'title': 'Уведомления'}  # Дополнительный контекст для шаблона (заголовок страницы).
    template_name = 'main/notification_list.html'  # Шаблон для отображения уведомлений.
    context_object_name = 'notifications_and_notices'  # Имя контекста для доступа к уведомлениям в шаблоне.
    paginate_by = 15  # Количество уведомлений на странице.

    def get_queryset(self) -> list[Notification | Notice]:
        # Метод для получения списка уведомлений (непрочитанных).
        return self.get_notifications(is_read=False)

    def get_notifications(self, is_read: bool, notification_type: str = None) -> list[Notification | Notice]:
        # Метод для получения уведомлений и уведомлений (notice).
        notifications = Notification.objects.filter(user=self.request.user,
                                                    is_read=is_read)  # Получаем уведомления текущего пользователя по статусу прочтения.
        notices = Notice.objects.filter(user=self.request.user,
                                        is_read=is_read)  # Получаем уведомления (notice) текущего пользователя по статусу прочтения.

        if notification_type == 'notification':
            return notifications.order_by(
                '-created_at')  # Если тип - уведомление, сортируем по времени создания (новые первыми).
        elif notification_type == 'notice':
            return notices.order_by(
                '-created_at')  # Если тип - notice, сортируем по времени создания (новые первыми).

        # Если тип не указан, возвращаем все уведомления и notice в отсортированном виде.
        return sorted(
            chain(notifications, notices),  # Объединяем списки уведомлений и notice.
            key=lambda instance: instance.created_at,
            reverse=True
        )


class ArchiveNotifications(NotificationListView):
    """ Представление для отображения архивных уведомлений"""
    extra_context = {'title': 'Архив уведомлений'}  # Заголовок для страницы архива уведомлений.

    def get_queryset(self) -> list[Notification | Notice]:
        notification_type = self.request.GET.get('type', None)
        notifications = self.get_notifications(is_read=True, notification_type=notification_type)
        return notifications


class NotificationReadView(View):
    """ Представление для чтения комментариев из уведомлений"""
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return redirect(notification.comment.post.get_absolute_url())


class NoticeReadView(View):
    """ Представление для чтения уведомлений"""
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        notice = get_object_or_404(Notice, pk=pk, user=request.user)
        notice.is_read = True
        notice.save(update_fields=['is_read'])
        if request.user.status == get_user_model().Status.LEADER:
            return redirect('study:leader_results')
        elif not notice.is_study:
            return redirect('users:profile')
        return redirect('study:result')


@login_required
def contact_view(request: HttpRequest) -> HttpResponse:
    """Представление для обратной связи"""
    initial_data = {
        'username': request.user.username,
        'email': request.user.email}
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            # Проверка на количество отправленных сообщений за день
            today = timezone.now().date()
            sent_count = SentMessage.objects.filter(user=request.user, timestamp__date=today,
                                                    purpose=SentMessage.PURPOSE.CONTACT).count()

            if sent_count >= 3:
                return render(request, 'users/contact_form.html', {
                    'form': form,
                    'error': 'Вы достигли лимита отправки сообщений на сегодня.'
                })
            # Формирование текста сообщения
            full_message = f"Имя: {username}\nEmail: {email}\nСообщение:\n{message}"
            # Отправка письма администратору
            send_mail(
                subject='Обратная связь',
                message=full_message,
                from_email=EMAIL_HOST_USER,
                recipient_list=[EMAIL_RECIPIENT_LIST],
            )
            # Сохранение информации о отправленном сообщении
            SentMessage.objects.create(user=request.user, purpose=SentMessage.PURPOSE.CONTACT)
            return render(request, 'main/contact_success.html')  # Страница успешной отправки
    else:
        form = ContactForm(initial=initial_data)
    return render(request, 'main/contact_form.html', {'form': form})


class LoginHistoryView(LoginRequiredMixin, ListView):
    """Представление для просмотра истории входа пользователя"""
    model = UserLoginHistory
    template_name = 'main/login_history.html'
    context_object_name = 'history'
    ordering = ['-login_time']
    paginate_by = 20

    def get_queryset(self):
        # Фильтруем историю входов для текущего пользователя
        return super().get_queryset().filter(user=self.request.user)


def tr_handler404(request: HttpRequest, exception: Exception) -> HttpResponse:
    """
    Обработка ошибки 404
    """
    return render(request=request, template_name='main/errors/error_page.html', status=404, context={
        'title': 'Страница не найдена: 404',
        'error_message': 'К сожалению такая страница была не найдена, или перемещена',
    })


def tr_handler500(request: HttpRequest) -> HttpResponse:
    """
    Обработка ошибки 500
    """
    return render(request=request, template_name='main/errors/error_page.html', status=500, context={
        'title': 'Ошибка сервера: 500',
        'error_message': 'Внутренняя ошибка сайта, вернитесь на главную страницу, отчет об ошибке мы направим администрации сайта',
    })


def tr_handler403(request: HttpRequest, exception: Exception) -> HttpResponse:
    """
    Обработка ошибки 403
    """
    return render(request=request, template_name='main/errors/error_page.html', status=403, context={
        'title': 'Ошибка доступа: 403',
        'error_message': 'Доступ к этой странице ограничен',
    })
