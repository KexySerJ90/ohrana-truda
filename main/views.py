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
from ohr.settings import EMAIL_HOST_USER, EMAIL_RECIPIENT_LIST, PHONE, DEFAULT_USER_IMAGE
from users.models import Departments
from users.permissions import StatusRequiredMixin


class IndexView(ListView):
    queryset = Article.published
    template_name = 'main/index.html'  # Укажите шаблон для отображения

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'Home - Охрана труда'
        context['content'] = "Охрана труда"
        context['arts'] = Article.published.all()[:3]

        return context


@require_safe
def about(request: HttpRequest) -> HttpResponse:
    return render(request, 'main/about.html', context = {
        'title': 'Home - О нас',
    })


class UploadFileView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'main/addfile.html'
    form_class = UploadFileForm
    success_url = reverse_lazy('main:add_file')

    def form_valid(self, form):
        category = form.cleaned_data['cat']
        files: List[Any] = self.request.FILES.getlist('files')
        is_common: bool = category.is_inpatient
        departments = Departments.objects.filter(is_inpatient=is_common)
        if is_common:
            # Создаем общие записи для каждого файла
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
            for uploaded_file in files:
                UploadFiles.objects.create(file=uploaded_file, cat=category, is_common=False)

        return super().form_valid(form)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['files'] = UploadFiles.objects.all()
        return context

    def test_func(self) -> bool:
        return self.request.user.is_staff or self.request.user.is_superuser


class Mainfiles(LoginRequiredMixin, StatusRequiredMixin, AuthorPermissionsMixin, ListView):
    template_name = 'main/mainfiles.html'
    context_object_name = 'posts'
    paginate_by = 6

    def get_queryset(self):
        if self.has_permissions():
            queryset = UploadFiles.objects.filter(cat__slug=self.kwargs['dep_slug'])
            order_by = self.request.GET.get('order_by', '')
            if order_by == 'title':
                queryset = queryset.order_by('title')
            elif order_by == '-title':
                queryset = queryset.order_by('-title')
            elif order_by == 'uploaded_at':
                queryset = queryset.order_by('uploaded_at')
            elif order_by == '-uploaded_at':
                queryset = queryset.order_by('-uploaded_at')
            return queryset
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        department = Departments.objects.get(slug=self.kwargs['dep_slug'])
        context['title'] = f'Файлы - {department.name}'  # Здесь предполагается, что название отделения хранится в поле name
        return context


class ArticlePosts(DataMixin, ListView):
    template_name = 'main/posts.html'
    context_object_name = 'posts'
    title_page = 'Статьи'
    cat_selected = 0

    def get_queryset(self):
        return Article.published.select_related('category').prefetch_related('ratings')


class AddPostView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = AddPostForm
    template_name = 'main/addpage.html'
    extra_context = {'title': 'Добавление статьи'}

    def test_func(self) -> bool:
        return self.request.user.is_staff or self.request.user.is_superuser


class ShowPost(DataMixin, DetailView):
    template_name = 'main/post.html'
    slug_url_kwarg = 'post_slug'
    context_object_name = 'post'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        post = context['post']
        context['form'] = CommentCreateForm
        return self.get_mixin_context(context, title=post.title)

    def get_object(self, queryset=None) -> Article:
        # Получаем объект статьи
        article = get_object_or_404(Article.published.prefetch_related('comments__user__profile'),
                                    slug=self.kwargs[self.slug_url_kwarg])
        ip_address = get_client_ip(self.request)
        if not UniqueView.objects.filter(article=article, ip_address=ip_address).exists():
            # Если нет, создаем новый объект UniqueView
            UniqueView.objects.create(article=article, ip_address=ip_address)

            # Увеличиваем количество уникальных просмотров
        article.views = article.unique_views.count()  # Обновляем общее количество просмотров
        article.save(update_fields=['views'])  # Сохраняем только поле views
        # Увеличиваем количество просмотров
        return article


class UpdatePage(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Article
    fields = ['title', 'content', 'photo', 'is_published', 'category', 'tags']
    template_name = 'main/addpage.html'
    success_url = reverse_lazy('main:home')
    extra_context = {'title': 'Редактирование статьи'}
    permission_required = 'main.change_article'


class ArticleCategory(DataMixin, ListView):
    template_name = 'main/posts.html'
    context_object_name = 'posts'
    allow_empty = False

    def get_queryset(self):
        return Article.published.filter(category__slug=self.kwargs['cat_slug']).select_related("category")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if context['posts']:
            cat = context['posts'][0].category
            context = self.get_mixin_context(context,
                                             title='Категория - ' + cat.name,
                                             cat_selected=cat.pk)
        return context


class PostSearchView(View):
    form_class = SearchForm
    template_name = 'main/search.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        query = None
        results_files = []
        results_articles = []

        if 'query' in request.GET:
            form = self.form_class(request.GET)
            if form.is_valid():
                A = 1.0
                B = 0.4
                query = form.cleaned_data['query']
                results_files = UploadFiles.objects.annotate(
                    similarity=TrigramSimilarity('file', query),
                ).filter(similarity__gt=0.07).order_by('title', '-similarity').distinct('title')

                results_articles = Article.objects.annotate(
                    similarity=(A / (A + B) * TrigramSimilarity('title', query)
                                + B / (A + B) * TrigramWordSimilarity(query, 'content'))
                ).filter(similarity__gt=0.25).order_by('-similarity')

        context = {
            'form': form,
            'query': query,
            'results_files': results_files,
            'results_articles': results_articles
        }
        return render(request, self.template_name, context)
        # search_vector = SearchVector('title', weight='A') + \
        #                 SearchVector('body', weight='B')
        # search_query = SearchQuery(query)
        # results = Post.published.annotate(
        #     search=search_vector,
        #     rank=SearchRank(search_vector, search_query)
        # ).filter(search=search_query).order_by('-rank')


class TagPostList(DataMixin, ListView):
    template_name = 'main/posts.html'
    context_object_name = 'posts'
    allow_empty = False

    def get_context_data(self, *, object_list: Optional[List[Article]] = None, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        tag = TagPost.objects.get(slug=self.kwargs['tag_slug'])
        return self.get_mixin_context(context, title='Тег: ' + tag.tag)

    def get_queryset(self):
        return Article.published.filter(tags__slug=self.kwargs['tag_slug']).select_related('category')


class RatingCreateView(View):
    model = Rating

    def post(self, request, *args, **kwargs):
        post_id = request.POST.get('post_id')
        value = int(request.POST.get('value'))
        ip_address = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None
        # Для неавторизованных пользователей
        if user is None:
            rating_queryset = self.model.objects.filter(post_id=post_id, ip_address=ip_address, user=None)
        else:  # Для авторизованных пользователей
            rating_queryset = self.model.objects.filter(post_id=post_id, user=user)

        if rating_queryset.exists():
            rating = rating_queryset.first()
            if rating.value == value:
                rating.delete()
                return JsonResponse({'status': 'deleted', 'rating_sum': rating.post.get_sum_rating()})
            else:
                rating.value = value
                if user is None:  # Обновляем ip_address только для неавторизованных пользователей
                    rating.ip_address = ip_address
                rating.save()
                return JsonResponse({'status': 'updated', 'rating_sum': rating.post.get_sum_rating()})
        else:
            # Создаем новый рейтинг
            rating = self.model.objects.create(
                post_id=post_id,
                user=user,
                ip_address=ip_address,
                value=value,
            )
            return JsonResponse({'status': 'created', 'rating_sum': rating.post.get_sum_rating()})


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentCreateForm

    def is_ajax(self) -> bool:
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def form_invalid(self, form: CommentCreateForm) -> JsonResponse:
        if self.is_ajax():
            return JsonResponse({'error': form.errors}, status=400)
        return super().form_invalid(form)

    def form_valid(self, form: CommentCreateForm) -> JsonResponse:
        locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
        comment = form.save(commit=False)
        comment.post_id = self.kwargs.get('pk')
        comment.user = self.request.user
        comment.parent_id = form.cleaned_data.get('parent')
        comment.save()
        if 'image' in self.request.FILES:
            image_file = self.request.FILES['image']
            comment.image.save(image_file.name, image_file)
        parent_comment_id = comment.parent_id
        if parent_comment_id:
            parent_comment = get_object_or_404(Comment, id=parent_comment_id)
            if parent_comment.user != comment.user:
                Notification.objects.create(user=parent_comment.user, comment=comment)
        if self.is_ajax():
            return JsonResponse({
                'is_child': comment.is_child_node(),
                'id': comment.id,
                'author': comment.user.username,
                'parent_id': comment.parent_id,
                'time_create': format_datetime(comment.time_create, format='dd MMMM yyyy г. HH:mm', locale='ru'),
                'photo': comment.user.profile.photo.url if comment.user.profile.photo else DEFAULT_USER_IMAGE,
                'content': comment.content,
            }, status=200)

        return redirect(comment.post.get_absolute_url())

    def handle_no_permission(self) -> JsonResponse:
        return JsonResponse({'error': 'Необходимо авторизоваться для добавления комментариев'}, status=400)


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment

    def is_ajax(self) -> bool:
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        comment = get_object_or_404(Comment, pk=kwargs['pk'], user=request.user)
        comment.delete()
        if self.is_ajax():
            return JsonResponse({'success': True}, status=200)
        return redirect(comment.post.get_absolute_url())

    def handle_no_permission(self) -> JsonResponse:
        return JsonResponse({'error': 'Необходимо авторизоваться для удаления комментариев'}, status=403)


class NotificationListView(LoginRequiredMixin, ListView):
    extra_context = {'title': 'Уведомления'}
    template_name = 'main/notification_list.html'
    context_object_name = 'notifications_and_notices'

    def get_queryset(self) -> list[Notification | Notice]:
        return self.get_notifications(is_read=False)


    def get_notifications(self, is_read: bool, notification_type: str = None) -> list[Notification | Notice]:
        notifications = Notification.objects.filter(user=self.request.user, is_read=is_read)
        notices = Notice.objects.filter(user=self.request.user, is_read=is_read)

        if notification_type == 'notification':
            return notifications.order_by('-created_at')
        elif notification_type == 'notice':
            return notices.order_by('-created_at')
        # Если тип не указан, возвращаем все
        return sorted(
            chain(notifications, notices),
            key=lambda instance: instance.created_at,
            reverse=True
        )


class ArchiveNotifications(NotificationListView):
    extra_context = {'title': 'Архив уведомлений'}

    def get_queryset(self) -> list[Notification | Notice]:
        notification_type = self.request.GET.get('type', None)
        notifications = self.get_notifications(is_read=True, notification_type=notification_type)
        return notifications



class NotificationReadView(View):
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return redirect(notification.comment.post.get_absolute_url())


class NoticeReadView(View):
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
    return render(request, 'main/contact_form.html', {'form': form, 'phone': PHONE})

class LoginHistoryView(LoginRequiredMixin, ListView):
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
