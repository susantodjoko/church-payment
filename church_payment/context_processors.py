def user_role(request):
    if request.user.is_authenticated:
        is_admin = (
            request.user.is_superuser
            or request.user.groups.filter(name='Super Admin').exists()
        )
        unconfirmed_count = 0
        if is_admin:
            from payments.models import Payment
            unconfirmed_count = Payment.objects.filter(
                date_reported__isnull=False,
                date_confirmed__isnull=True,
            ).count()
        return {'is_super_admin': is_admin, 'unconfirmed_count': unconfirmed_count}
    return {'is_super_admin': False, 'unconfirmed_count': 0}
