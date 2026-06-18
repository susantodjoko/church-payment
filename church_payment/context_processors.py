def user_role(request):
    if request.user.is_authenticated:
        is_admin = (
            request.user.is_superuser
            or request.user.groups.filter(name='Super Admin').exists()
        )
        return {'is_super_admin': is_admin}
    return {'is_super_admin': False}
