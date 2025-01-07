from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views import View


class ProfileRequiredMixin(View):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('users:profile')
        return super().dispatch(request, *args, **kwargs)


class StatusRequiredMixin(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.status:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class NotSocialRequiredMixin(View):
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            if user.is_social_user:
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)