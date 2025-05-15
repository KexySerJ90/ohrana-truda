from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from main.models import Notice
from study.models import Subject, SubjectCompletion
from users.models import User

class BaseUserMixin:
    """Представление для установления параметров базового пользователя"""
    def handle_subjects(self, user):
        sub_titles = None
        if user.status == 'leader':
            if user.profile.profession.worker:
                sub_titles = ['first_aid', 'safe_method2', 'suot']
            else:
                sub_titles = ['first_aid', 'safe_method1', 'suot']
        elif user.status == 'medic':
            sub_titles = ['safe_method1']
        elif user.status == 'worker':
            sub_titles = ['first_aid', 'safe_method2']

        if sub_titles:
            subjects = Subject.objects.filter(title__in=sub_titles)
            for sub in subjects:
                subject_completion, created = SubjectCompletion.objects.get_or_create(users=user, subjects=sub)
                user.subject.add(sub)
                subject_completion.save()
        try:
            leader = get_user_model().objects.get(status=get_user_model().Status.LEADER, cat2=user.cat2)
            if leader != user:
                Notice.objects.create(
                    user=leader,
                    message=f"{user.profile.profession} {user.last_name} {user.first_name} завершил регистрацию")
        except ObjectDoesNotExist:
            pass
        Notice.objects.create(
            user=user,
            message=f"Поздравляем, вы завершили регистрацию!"
        )

class UserQuerysetMixin:
    """
    Миксин для получения queryset пользователей в зависимости от их статуса.
    """

    def get_user_queryset(self, user):
        """
        Возвращает queryset активных пользователей, если у пользователя есть соответствующие права доступа.

        Параметры:
        user (User): объект пользователя, для которого необходимо получить queryset.

        Возвращает:
        QuerySet: queryset активных пользователей, отфильтрованный по категории и отсортированный по статусу.

        """
        # Проверяем статус пользователя и его права
        if user.is_staff or user.is_superuser:
            return get_user_model().objects.filter(is_active=True).prefetch_related('subject_completions__subjects').select_related('profile__profession').order_by('cat2','status')
        if user.status == get_user_model().Status.LEADER or user.zamestitel:
            # Получаем активных пользователей с той же категорией и предзагружаем связанные данные
            return get_user_model().objects.filter(
                cat2=user.cat2,
                is_active=True
            ).prefetch_related('subject_completions__subjects').select_related('profile__profession').order_by('status')

        # Если у пользователя нет прав доступа, выбрасываем исключение
        raise PermissionDenied("You do not have permission to access this resource.")


def create_notice_if_not_exists(user, role, subject):
    """Создает уведомление для пользователя, если оно еще не существует."""
    subject_message = f"Пользователь {user.first_name} {user.last_name} сдал тест по предмету '{subject}'."
    if not Notice.objects.filter(
            user=role,
            message__contains=subject_message,
    ).exists():
        Notice.objects.create(user=role, message=subject_message, is_study = True)

