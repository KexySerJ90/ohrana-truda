from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, RedirectView

from main.models import Notice
from study.models import Subject, SubjectCompletion, Video, Answer, Question, UserAnswer
from study.utils import UserQuerysetMixin, create_notice_if_not_exists
from users.models import Profile, User
from users.permissions import StatusRequiredMixin


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
                progress.current_slide = None
                # Обучение завершено
                progress.study_completed = True  # Сброс текущего слайда
                progress.save()
                return render(request, 'study/learning/learning_complete.html', context={'subject': subject})

        elif 'previous' in request.POST and current_slide_index > 0:
            progress.current_slide = slides[current_slide_index - 1]
            progress.save()

        elif 'reset_subject' in request.POST:
            # Сброс текущего слайда и завершения обучения
            progress.current_slide = slides[0]  # Устанавливаем первый слайд
            progress.save()
            return redirect('study:subject_detail', subject_slug=subject.slug)

        return redirect('study:subject_detail', subject_slug=subject.slug)

    context = {
        'subject': subject,
        'current_slide': current_slide,
        'is_last_slide': current_slide_index == len(slides) - 1,
        'current_slide_index': current_slide_index,
        'study_completed': progress.study_completed,
        'title': f'{subject.get_title_display()} - {current_slide_index + 1}'
    }

    if progress.study_completed and not progress.current_slide:
        context['title'] = f'{subject.get_title_display()} - Завершено'
        return render(request, 'study/learning/learning_complete.html', context)

    return render(request, 'study/learning/subject_detail.html', context)


class VideoInstruktajView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, video_slug: str) -> HttpResponse:
        profile = Profile.objects.get(user=request.user)
        video = get_object_or_404(Video, slug=video_slug)
        answers = video.answers.all()  # Получаем ответы для текущего видео
        if video.slug == 'finish':
            profile.instructaj = True
            profile.save()
        return render(request, 'study/video_player/video.html',
                      {'video': video, 'answers': answers, 'title': f'Вводный инструктаж-{video}'})


class AnswerView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        answer = get_object_or_404(Answer, id=kwargs['answer_id'])
        next_video = answer.next_video
        return reverse_lazy('study:video_detail', kwargs={'video_slug': next_video.slug})


@login_required
def test_view(request: HttpRequest, test_slug: str) -> HttpResponse:
    subject = get_object_or_404(Subject, slug=test_slug)
    user_completion = get_object_or_404(SubjectCompletion, users=request.user, subjects=subject)
    incorrect_answers = user_completion.user_answers.exclude(selected_answer=F('question__correct_option'))
    if 'questions' in request.session and request.session['questions'] and request.session['subject'] == subject.id:
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
        return redirect('study:test', test_slug=subject.slug)
    if user_completion.completed:
        del request.session['questions']
        del request.session['subject']
        request.session.pop('test_time_remaining', None)
        return render(request, 'study/test_result.html', {
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
        answers_to_create = []
        for question in questions:
            answer = request.POST.get(f'question_{question.id}')
            if answer:
                selected_answer = int(answer)
                user_completion.score += selected_answer == question.correct_option
                answers_to_create.append(UserAnswer(
                    user_completion=user_completion,
                    question=question,
                    selected_answer=selected_answer
                ))
        # Создаем все объекты сразу одной операцией
        UserAnswer.objects.bulk_create(answers_to_create)
        if user_completion.score >= len(questions) - 3:
            user_completion.completed = True
            leaders = get_user_model().objects.filter(
                status=User.Status.LEADER,
                cat2=request.user.cat2
            ).exclude(pk=request.user.pk)  # Исключаем текущего пользователя
            admins = get_user_model().objects.filter(is_superuser=True)
            for leader in leaders:
                create_notice_if_not_exists(user=request.user, role=leader,subject= subject)
            for admin in admins:
                create_notice_if_not_exists(user=request.user, role=admin, subject=subject)
            Notice.objects.create(
                user=request.user,
                message=f"Поздравляем, вы прошли обучение по предмету '{subject}'!",
                is_study = True
            )
        user_completion.save()
        del request.session['questions']
        del request.session['subject']
        del request.session['test_time_remaining']
        return render(request, 'study/test_result.html',
                      {'score': user_completion.score, 'total': len(questions), 'passed': user_completion.completed,
                       'subject': subject, 'incorrect_answers': incorrect_answers,
                       'title': f'Тест не сдан по {subject}'})
    request.session['test_time_remaining'] = time_remaining
    return render(request, 'study/test.html',
                  {'subject': subject, 'questions': questions, 'user_completion': user_completion,
                   'time_remaining': time_remaining, 'title': f'Тестирование по {subject}'})


class MyResult(LoginRequiredMixin, StatusRequiredMixin, ListView):
    model = get_user_model()
    template_name = 'study/results.html'
    extra_context = {'title': "Мои результаты"}

    # def get_queryset(self):
    #     user = self.request.user
    #     return User.objects.prefetch_related('subject_completions__subjects').filter(pk=user.pk)

    def get_object(self, queryset=None):
        return self.request.user


class LeaderResultsView(LoginRequiredMixin, ListView, UserQuerysetMixin):
    template_name = 'study/leader_results.html'
    paginate_by = 4
    context_object_name = 'users'
    extra_context = {'title': "Результаты подразделения"}

    def get_queryset(self):
        user = self.request.user
        return self.get_user_queryset(user)
