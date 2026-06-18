from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class SuperAdminRequired(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        is_admin = (
            request.user.is_superuser
            or request.user.groups.filter(name='Super Admin').exists()
        )
        if not is_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
