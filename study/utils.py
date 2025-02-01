from django.core.exceptions import PermissionDenied

from main.models import Notice
from users.models import User


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
        if user.status == User.Status.LEADER or user.is_superuser or user.is_staff:
            # Получаем активных пользователей с той же категорией и предзагружаем связанные данные
            return User.objects.filter(
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