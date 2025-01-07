
# - Import password reset token generator

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import six


# - Password reset token generator method

class UserVerificationTokenGenerator(PasswordResetTokenGenerator):
    # Определение метода _make_hash_value, который принимает пользователя и метку времени
    def _make_hash_value(self, user, timestamp):
        # Преобразование идентификатора пользователя в текстовый формат
        user_id = six.text_type(user.pk)
        # Преобразование метки времени в текстовый формат
        ts = six.text_type(timestamp)
        # Преобразование статуса активности пользователя в текстовый формат
        is_active = six.text_type(user.is_active)
        # Возвращение конкатенации идентификатора пользователя, метки времени и статуса активности
        return f"{user_id}{ts}{is_active}"


user_tokenizer_generate = UserVerificationTokenGenerator()