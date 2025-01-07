from typing import Any, Dict, List, Optional
from django.http import HttpRequest, HttpResponse
import locale
from itertools import chain

from babel.dates import format_datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.contrib.postgres.search import TrigramSimilarity, TrigramWordSimilarity
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.http import require_safe
from django.views.generic import FormView, CreateView, ListView, DetailView, UpdateView, DeleteView

from main.forms import UploadFileForm, SearchForm, AddPostForm, CommentCreateForm
from main.models import UploadFiles, Article, Departments, TagPost, Rating, Subject, Question, Video, Answer, \
    Comment
from main.permissions import AuthorPermissionsMixin
from main.utils import DataMixin

from users.models import SubjectCompletion, UserAnswer, User, Notice, Notification
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
            return UploadFiles.objects.filter(cat__slug=self.kwargs['dep_slug'])
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
        # Увеличиваем количество просмотров
        article.views += 1
        article.save(update_fields=['views'])  # Сохраняем только поле views
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
                query = form.cleaned_data['query']

                results_files = UploadFiles.objects.annotate(
                    similarity=TrigramSimilarity('file', query),
                ).filter(similarity__gt=0.05).order_by('-similarity')

                results_articles = Article.objects.annotate(
                    similarity=TrigramSimilarity('title', query),
                ).filter(similarity__gt=0.05).order_by('-similarity')

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
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
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


@login_required
def subject_detail(request: HttpRequest, subject_slug: str) -> HttpResponse:
    subject = get_object_or_404(Subject, slug=subject_slug)
    progress = get_object_or_404(SubjectCompletion, users=request.user, subjects=subject)

    slides = list(subject.slides.all())
    current_slide_index = slides.index(progress.current_slide) if progress.current_slide else 0
    current_slide = slides[current_slide_index]

    if request.method == 'POST':
        if 'next' in request.POST:
            if current_slide_index < len(slides) - 1:
                progress.current_slide = slides[current_slide_index + 1]
                progress.save()
            else:
                # Обучение завершено
                progress.study_completed = True  # Сброс текущего слайда
                progress.save()
                return render(request, 'main/learning/learning_complete.html', context={'subject': subject})

        elif 'previous' in request.POST and current_slide_index > 0:
            progress.current_slide = slides[current_slide_index - 1]
            progress.save()

        elif 'reset_subject' in request.POST:
            # Сброс текущего слайда и завершения обучения
            progress.current_slide = slides[0]  # Устанавливаем первый слайд
            progress.save()
            return redirect('main:subject_detail', subject_slug=subject.slug)

        return redirect('main:subject_detail', subject_slug=subject.slug)

    context = {
        'subject': subject,
        'current_slide': current_slide,
        'is_last_slide': current_slide_index == len(slides) - 1,
        'current_slide_index': current_slide_index,
        'study_completed': progress.study_completed,
        'title': f'{subject.get_title_display()} - {current_slide_index + 1}'
    }

    if progress.study_completed and current_slide_index >= len(slides) - 1:
        context['title'] = f'{subject.get_title_display()} - Завершено'
        return render(request, 'main/learning/learning_complete.html', context)

    return render(request, 'main/learning/subject_detail.html', context)


@login_required
def video_view(request: HttpRequest, video_slug: str) -> HttpResponse:
    user = request.user
    video = get_object_or_404(Video, slug=video_slug)
    answers = video.answers.all()  # Получаем ответы для текущего видео
    if video.slug == 'finish':
        user.instructaj = True
        user.save()
    return render(request, 'main/video_player/video.html',
                  {'video': video, 'answers': answers, 'title': f'Вводный инструктаж-{video}'})


@login_required
def answer_view(request: HttpRequest, answer_id: int) -> HttpResponse:
    answer = get_object_or_404(Answer, id=answer_id)
    next_video = answer.next_video
    return redirect('main:video_detail', video_slug=next_video.slug)


@login_required
def test_view(request: HttpRequest, test_slug: str) -> HttpResponse:
    subject = get_object_or_404(Subject, slug=test_slug)
    user_completion = get_object_or_404(SubjectCompletion, users=request.user, subjects=subject)
    incorrect_answers = user_completion.user_answers.exclude(selected_answer=F('question__correct_option'))
    if 'questions' in request.session and request.session['questions'] and 'subject' in request.session and \
            request.session['subject'] == subject.id:
        question_ids = request.session['questions']
        questions = Question.objects.filter(id__in=question_ids)
    else:
        questions = Question.objects.filter(subject=subject).order_by('?')[:10]
        request.session['questions'] = [question.id for question in questions]
        request.session['subject'] = subject.id
    time_remaining = request.session.get('test_time_remaining', 600)
    if 'reset_test' in request.POST:
        # Сброс результатов
        user_completion.score = 0
        user_completion.completed = False
        user_completion.user_answers.all().delete()
        user_completion.save()
        request.session['questions'] = None
        request.session['test_time_remaining'] = 600
        return redirect('main:test', test_slug=subject.slug)
    if user_completion.completed:
        request.session.pop('test_time_remaining', None)
        return render(request, 'main/test_result.html', {
            'subject': subject,
            'score': user_completion.score,
            'total': len(questions),
            'passed': user_completion.completed,
            'title': f'Тест {subject} завершен'
        })
    if request.method == 'POST':
        if not user_completion.completed:
            user_completion.score = 0
            user_completion.user_answers.all().delete()
        for question in questions:
            answer = request.POST.get(f'question_{question.id}')
            if answer:
                selected_answer = int(answer)
                user_completion.score += selected_answer == question.correct_option
                UserAnswer.objects.create(
                    user_completion=user_completion,
                    question=question,
                    selected_answer=selected_answer
                )
        if user_completion.score >= len(questions) - 3:
            user_completion.completed = True
            subject_message = f"Пользователь {request.user.first_name} {request.user.last_name} сдал тест по предмету '{subject}'."
            leaders = get_user_model().objects.filter(status=User.Status.LEADER, cat2=request.user.cat2)
            # Получаем админа (предположим, у вас есть пользователь с ролью 'admin')
            admins = get_user_model().objects.filter(
                is_superuser=True)  # Или используйте другой фильтр для определения админов
            for leader in leaders:
                if leader != request.user:
                    if not Notice.objects.filter(user=leader, message__icontains=subject).exists():
                        Notice.objects.create(
                            user=leader,
                            message=subject_message
                        )
            for admin in admins:
                if not Notice.objects.filter(user=admin, message__icontains=subject).exists():
                    Notice.objects.create(
                        user=admin,
                        message=subject_message
                    )
            Notice.objects.create(
                user=request.user,
                message=f"Поздравляем, вы прошли обучение по предмету '{subject}'!"
            )
        user_completion.save()
        return render(request, 'main/test_result.html',
                      {'score': user_completion.score, 'total': len(questions), 'passed': user_completion.completed,
                       'subject': subject, 'incorrect_answers': incorrect_answers,
                       'title': f'Тест не сдан по {subject}'})
    request.session['test_time_remaining'] = time_remaining
    return render(request, 'main/test.html',
                  {'subject': subject, 'questions': questions, 'user_completion': user_completion,
                   'time_remaining': time_remaining, 'title': f'Тестирование по {subject}'})


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
                'photo': comment.user.photo.url,
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
            return redirect('users:leader_results')
        return redirect('users:result')


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
