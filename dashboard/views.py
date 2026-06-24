from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum
from members.models import Member, Wilayah
from payments.models import Payment, PaymentType


@login_required
def index(request):
    now = timezone.localtime(timezone.now())
    month, year = now.month, now.year

    this_month_payments = Payment.objects.filter(period_month=month, period_year=year)
    total_collected = this_month_payments.aggregate(t=Sum('amount'))['t'] or 0
    transaction_count = this_month_payments.count()

    paid_ids = this_month_payments.filter(
        member__isnull=False
    ).values_list('member_id', flat=True).distinct()
    total_members = Member.objects.filter(is_active=True).count()
    unpaid_count = total_members - Member.objects.filter(is_active=True, pk__in=paid_ids).count()

    recent_payments = Payment.objects.select_related(
        'member', 'payment_type'
    ).order_by('-date_received')[:10]

    wilayah_stats = []
    for w in Wilayah.objects.all():
        total = Payment.objects.filter(
            period_month=month, period_year=year,
            member__lingkungan__wilayah=w
        ).aggregate(t=Sum('amount'))['t'] or 0
        wilayah_stats.append({'wilayah': w, 'total': total})

    return render(request, 'dashboard/index.html', {
        'month': month, 'year': year,
        'total_collected': total_collected,
        'transaction_count': transaction_count,
        'total_members': total_members,
        'unpaid_count': unpaid_count,
        'recent_payments': recent_payments,
        'wilayah_stats': wilayah_stats,
    })
