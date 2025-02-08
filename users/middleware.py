class UpdateLastActivityMiddleware:
    """
        Middleware для обновления времени последней активности пользователя.
        Этот middleware проверяет, аутентифицирован ли пользователь при каждом запросе.
        Если пользователь аутентифицирован, вызывается метод update_last_activity(),
        который обновляет время последней активности пользователя.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user.update_last_activity()  # Обновление времени последней активности
        response = self.get_response(request)
        return response