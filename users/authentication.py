from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend, ModelBackend
from django.db.models import Q

from users.token import user_tokenizer_generate


class EmailAuthBackend(BaseBackend):
    supports_object_permissions=True
    supports_anonymous_user=False
    supports_inactive_user=False

    # def authenticate(self, request, username=None, password=None, **kwargs):
    #     user_model = get_user_model()
    #     try:
    #         user = user_model.objects.get(email=username)
    #         if user.check_password(password):
    #             return user
    #         return None
    #     except (user_model.DoesNotExist, user_model.MultipleObjectsReturned):
    #         return None

    def authenticate(self, request, username=None, password=None, token=None, **kwargs):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(Q(username=username) | Q(email=username) | Q(phone=username))
            if user.check_password(password):
                # Проверка токена
                if token and user_tokenizer_generate.check_token(user, token):
                    return user
                elif not token:
                    # Если токен не предоставлен, можно вернуть пользователя только если он активен
                    return user if user.is_active else None
            return None
        except (user_model.DoesNotExist, user_model.MultipleObjectsReturned):
            return None

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
