from typing import Any, Dict, List, Optional
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse
import locale
from itertools import chain
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
from main.models import UploadFiles, Article, Departments, TagPost, Rating, Comment, UniqueView, JobDetails
from main.permissions import AuthorPermissionsMixin
from main.utils import DataMixin, get_client_ip
from ohr.settings import EMAIL_HOST_USER, EMAIL_RECIPIENT_LIST, PHONE
from users.forms import ProfessionForm
from users.models import Notice, Notification, SentMessage, Profession
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
    context = {
        'title': 'Home - О нас',
        'content': "О нас",
        'text_on_page': "Текст о том почему мы классные."
    }

    return render(request, 'main/about.html', context)


# def upload_and_display_files(request):
#     files = UploadFiles.objects.all()
#     if request.method == 'POST':
#         form = UploadFileForm(request.POST, request.FILES)
#         if form.is_valid():
#             category = form.cleaned_data['cat']
#             for uploaded_file in request.FILES.getlist('files'):
#                 UploadFiles.objects.create(file=uploaded_file, cat=category)
#             return redirect('main:add_page')
#     else:
#         form = UploadFileForm()
#
#     return render(request, 'main/addfile.html', {'form': form, 'files': files})

class UploadFileView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'main/addfile.html'
    form_class = UploadFileForm
    success_url = reverse_lazy('main:add_file')

    def form_valid(self, form):
        category = form.cleaned_data['cat']
        files: List[Any] = self.request.FILES.getlist('files')
        is_common: bool = category.is_inpatient
        departments = Departments.objects.filter(is_inpatient=is_common)
        for uploaded_file in files:
            if category.is_inpatient:
                for department in departments:
                    # UploadFiles.objects.create(file=uploaded_file, cat=department, is_common=is_common)
                    UploadFiles.objects.bulk_create(
                        [UploadFiles(file=uploaded_file, cat=department, is_common=is_common)])
            else:
                # mainfiles = Departments.objects.get(id=1)
                # UploadFiles.objects.create(file=uploaded_file, cat=category)
                UploadFiles.objects.bulk_create([UploadFiles(file=uploaded_file, cat=category)])
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
    title_page = 'Общие файлы'
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


class ArticlePosts(DataMixin, ListView):
    template_name = 'main/posts.html'
    context_object_name = 'posts'
    title_page = 'Статьи'
    cat_selected = 0

    def get_queryset(self):
        return Article.published.select_related('category')


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
        article = get_object_or_404(Article.published.prefetch_related('comments__user'),
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
        cat = context['posts'][0].category
        return self.get_mixin_context(context,
                                      title='Категория - ' + cat.name,
                                      cat_selected=cat.pk, )


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
                ).filter(similarity__gt=0.05).order_by('title','-similarity').distinct('title')

                results_articles = Article.objects.annotate(
                    similarity=(A / (A + B) * TrigramSimilarity('title', query)
                                + B / (A + B) * TrigramWordSimilarity(query, 'content'))
                ).filter(similarity__gt=0.06).order_by('-similarity')

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
        # A = 1.0
        # B = 0.4


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
        ip_address=get_client_ip(request)
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
                'photo': comment.user.profile.photo.url,
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
    template_name = 'main/notification_list.html'
    context_object_name = 'notifications_and_notices'

    def get_queryset(self) -> list[Notification | Notice]:
        # Получаем уведомления для текущего пользователя
        notifications = Notification.objects.filter(user=self.request.user, is_read=False).order_by('-created_at')

        # Получаем уведомления (Notice) для текущего пользователя
        notices = Notice.objects.filter(user=self.request.user, is_read=False).order_by('-created_at')

        # Объединяем оба QuerySet
        return sorted(
            chain(notifications, notices),
            key=lambda instance: instance.created_at,
            reverse=True
        )

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['notifications'] = Notification.objects.filter(user=self.request.user)
        context['notices'] = Notice.objects.filter(user=self.request.user)
        context['title'] = 'Уведомления'
        return context


class NotificationReadView(View):
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return redirect(notification.comment.post.get_absolute_url())


class NoticeReadView(View):
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        notice = get_object_or_404(Notice, pk=pk, user=request.user)
        notice.is_read = True
        notice.save()
        if request.user.status == get_user_model().Status.LEADER:
            return redirect('study:leader_results')
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
            sent_count = SentMessage.objects.filter(user=request.user, timestamp__date=today, purpose=SentMessage.PURPOSE.CONTACT).count()

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


class SIZForm(LoginRequiredMixin, FormView):
    template_name = 'main/siz_form.html'
    form_class = ProfessionForm
    extra_context = {'title': "Калькулятор СИЗ"}


class EquipmentListView(LoginRequiredMixin, View):
    def get(self, request) -> JsonResponse:
        profession_id = request.GET.get('profession_id')
        equipment_list = []

        if profession_id:
            profession = Profession.objects.get(id=profession_id)
            equipment_queryset = profession.equipment.all()

            for equipment in equipment_queryset:
                equipment_list.append({
                    'description': equipment.description,
                    'quantity': equipment.quantity,
                    'basis': equipment.basis,
                })

        return JsonResponse({'equipment': equipment_list})

class SOUTUserView(LoginRequiredMixin, DetailView):
    template_name = 'main/sout.html'
    model = JobDetails
    extra_context = {'title': "Результаты специальной оценки условий труда"}
    context_object_name = 'workplace'

    def get_object(self, queryset=None):
        user = self.request.user
        try:
            # Получаем рабочее место по профессии и отделению текущего пользователя
            obj = JobDetails.objects.get(
                profession=user.profile.profession,
                department=user.cat2
            )
        except JobDetails.DoesNotExist:
            obj = None
        return obj



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



