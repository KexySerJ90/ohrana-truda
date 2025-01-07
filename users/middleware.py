class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user.update_last_activity()  # Обновление времени последней активности
        response = self.get_response(request)
        return response