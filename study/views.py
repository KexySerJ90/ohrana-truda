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
from study.models import Subject, SubjectCompletion, Video, Answer, Question, UserAnswer, Achievement
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
                progress.save(update_fields=['current_slide'])
            else:
                progress.current_slide = None
                # Обучение завершено
                progress.study_completed = True  # Сброс текущего слайда
                progress.save(update_fields=['current_slide', 'study_completed'])
                Achievement.objects.get_or_create(user=request.user, type='finish_training')
                return render(request, 'study/learning/learning_complete.html', context={'subject': subject})

        elif 'previous' in request.POST and current_slide_index > 0:
            progress.current_slide = slides[current_slide_index - 1]
            progress.save(update_fields=['current_slide'])

        elif 'reset_subject' in request.POST:
            # Сброс текущего слайда и завершения обучения
            progress.current_slide = slides[0]  # Устанавливаем первый слайд
            progress.save(update_fields=['current_slide'])
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
            profile.save(update_fields=['instructaj'])
            Achievement.objects.get_or_create(user=self.request.user, type='intro_instruct')
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
            Achievement.objects.get_or_create(user=request.user, type='first_test')
            user_completion.save()
            exams=SubjectCompletion.objects.filter(users=request.user)
            if all(exam.completed for exam in exams):
                Achievement.objects.get_or_create(user=request.user, type='all_exams_passed')
            if user_completion.score == 5:
                Achievement.objects.get_or_create(user=request.user, type='free_tester')
                if all(exam.score == 5 for exam in exams):
                    Achievement.objects.get_or_create(user=request.user, type='master_of_exams')
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


class Achievements(LoginRequiredMixin, ListView):
    template_name = 'study/achievements.html'
    context_object_name = 'achieve'
    title_page = 'Достижения'
    model = Achievement

    ICONS_BY_TYPE = {
        'site_entry': 'house-door-fill',
        'intro_instruct': 'info-circle-fill',
        'finish_training': 'calendar-check',
        'first_test': 'check-circle-fill',
        'photo_profile': 'person-fill',
        'free_tester': 'pencil-square',
        'all_exams_passed': 'hand-thumbs-up-fill',
        'master_of_exams': 'cup-fill',
        'all_achievements': 'trophy-fill',
    }


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Получаем текущий пользователя
        user = self.request.user

        # Получаем все достижения пользователя за один запрос
        user_achievements = Achievement.objects.filter(user=user).values_list('type', flat=True)

        # Типы достижений
        achievements = Achievement.TYPE_CHOICES

        # Формируем словарь достижений с их статусом и иконкой
        context['achievements'] = []
        for achievement_type, achievement_label in achievements:
            status = achievement_type in user_achievements  # Проверяем наличие достижения
            icon_class = self.ICONS_BY_TYPE.get(achievement_type, 'star-fill')  # Иконка по типу достижения
            context['achievements'].append({
                'type': achievement_type,
                'label': achievement_label,
                'is_completed': status,
                'icon_class': icon_class
            })
        all_achievements_completed = all(
            achievement['is_completed'] for achievement in context['achievements']
            if achievement['type'] != 'all_achievements'
        )
        if all_achievements_completed and 'all_achievements' not in user_achievements:
            Achievement.objects.create(user=user, type='all_achievements')


        # Проверяем, выполнены ли все достижения
        context['all_complete'] = all(achievement['is_completed'] for achievement in context['achievements'])

        return context