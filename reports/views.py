from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count
from members.models import Member, Wilayah, Lingkungan
from payments.models import Payment, PaymentType
from .exporters import build_monthly_excel, build_annual_excel, build_unpaid_excel, build_lk_pkss_excel


def _recorded_by_filter(request):
    is_admin = (
        request.user.is_superuser
        or request.user.groups.filter(name='Super Admin').exists()
    )
    return {} if is_admin else {'recorded_by': request.user}


def _get_filter_context(request):
    now = timezone.localtime(timezone.now())
    try:
        month = int(request.GET.get('month', now.month))
    except (ValueError, TypeError):
        month = now.month
    try:
        year = int(request.GET.get('year', now.year))
    except (ValueError, TypeError):
        year = now.year
    return {
        'month': month,
        'year': year,
        'payment_type_id': request.GET.get('payment_type', ''),
        'wilayah_id': request.GET.get('wilayah', ''),
        'lingkungan_id': request.GET.get('lingkungan', ''),
        'now': now,
    }


@login_required
def report_index(request):
    now = timezone.localtime(timezone.now())
    return render(request, 'reports/index.html', {
        'payment_types': PaymentType.objects.filter(is_active=True),
        'wilayah_list': Wilayah.objects.all(),
        'years': range(now.year - 3, now.year + 2),
        'months': range(1, 13),
        'now': now,
    })


@login_required
def monthly_report(request):
    f = _get_filter_context(request)
    qs = Payment.objects.filter(
        period_month=f['month'], period_year=f['year'],
        **_recorded_by_filter(request),
    ).select_related('member__lingkungan__wilayah', 'keluarga__lingkungan__wilayah', 'payment_type', 'recorded_by')

    if f['payment_type_id']:
        qs = qs.filter(payment_type_id=f['payment_type_id'])
    if f['wilayah_id']:
        qs = qs.filter(member__lingkungan__wilayah_id=f['wilayah_id'])
    if f['lingkungan_id']:
        qs = qs.filter(member__lingkungan_id=f['lingkungan_id'])

    total = qs.aggregate(t=Sum('amount'))['t'] or 0
    return render(request, 'reports/monthly.html', {
        **f,
        'payments': qs,
        'total': total,
        'payment_types': PaymentType.objects.filter(is_active=True),
        'wilayah_list': Wilayah.objects.all(),
        'months': range(1, 13),
        'years': range(f['now'].year - 3, f['now'].year + 2),
    })


@login_required
def annual_report(request):
    f = _get_filter_context(request)
    year = f['year']

    rb = _recorded_by_filter(request)
    monthly_totals = []
    for m in range(1, 13):
        total = Payment.objects.filter(period_month=m, period_year=year, **rb).aggregate(
            t=Sum('amount'))['t'] or 0
        count = Payment.objects.filter(period_month=m, period_year=year, **rb).count()
        monthly_totals.append({'month': m, 'total': total, 'count': count})

    return render(request, 'reports/annual.html', {
        **f,
        'monthly_totals': monthly_totals,
        'grand_total': sum(r['total'] for r in monthly_totals),
        'years': range(f['now'].year - 3, f['now'].year + 2),
    })


@login_required
def unpaid_report(request):
    f = _get_filter_context(request)
    month, year = f['month'], f['year']
    pt_id = f['payment_type_id']

    paid_qs = Payment.objects.filter(
        period_month=month, period_year=year, member__isnull=False,
    )
    if pt_id:
        paid_qs = paid_qs.filter(payment_type_id=pt_id)
    paid_member_ids = paid_qs.values_list('member_id', flat=True)

    unpaid = Member.objects.filter(
        is_active=True
    ).exclude(pk__in=paid_member_ids).select_related('lingkungan__wilayah')

    if f['wilayah_id']:
        unpaid = unpaid.filter(lingkungan__wilayah_id=f['wilayah_id'])
    if f['lingkungan_id']:
        unpaid = unpaid.filter(lingkungan_id=f['lingkungan_id'])

    return render(request, 'reports/unpaid.html', {
        **f,
        'unpaid_members': unpaid,
        'payment_types': PaymentType.objects.filter(is_active=True),
        'wilayah_list': Wilayah.objects.all(),
        'months': range(1, 13),
        'years': range(f['now'].year - 3, f['now'].year + 2),
    })


@login_required
def export_monthly(request):
    f = _get_filter_context(request)
    qs = list(Payment.objects.filter(
        period_month=f['month'], period_year=f['year'],
        **_recorded_by_filter(request),
    ).select_related('member__lingkungan__wilayah', 'keluarga__lingkungan__wilayah', 'payment_type', 'recorded_by'))
    buf = build_monthly_excel(qs, f['month'], f['year'])
    filename = f"laporan-{f['month']}-{f['year']}.xlsx"
    response = HttpResponse(buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_annual(request):
    f = _get_filter_context(request)
    year = f['year']
    rb = _recorded_by_filter(request)
    monthly_totals = []
    for m in range(1, 13):
        total = Payment.objects.filter(period_month=m, period_year=year, **rb).aggregate(
            t=Sum('amount'))['t'] or 0
        count = Payment.objects.filter(period_month=m, period_year=year, **rb).count()
        monthly_totals.append([m, float(total), count])
    members = Member.objects.filter(is_active=True).select_related('lingkungan__wilayah')
    member_summary = []
    for mem in members:
        payments = Payment.objects.filter(member=mem, period_year=year, **rb)
        months_paid = payments.values('period_month').distinct().count()
        total = payments.aggregate(t=Sum('amount'))['t'] or 0
        member_summary.append([
            mem.full_name, mem.lingkungan.name,
            months_paid, float(total), 12 - months_paid
        ])

    buf = build_annual_excel(year, monthly_totals, member_summary)
    response = HttpResponse(buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="laporan-tahunan-{year}.xlsx"'
    return response


@login_required
def export_lk_pkss(request):
    now = timezone.localtime(timezone.now())
    try:
        year = int(request.GET.get('year', now.year))
    except (ValueError, TypeError):
        year = now.year

    lingkungan_list = list(
        Lingkungan.objects.select_related('wilayah').order_by('wilayah__name', 'name')
    )
    pkss_payments = list(
        Payment.objects.filter(
            payment_type__name='Iuran PKKS',
            period_year=year,
        ).select_related(
            'member__lingkungan__wilayah',
            'keluarga__lingkungan__wilayah',
        ).order_by('period_month', 'date_received')
    )

    buf = build_lk_pkss_excel(year, lingkungan_list, pkss_payments)
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="LK-PKSS-{year}.xlsx"'
    return response


@login_required
def export_unpaid(request):
    f = _get_filter_context(request)
    month, year, pt_id = f['month'], f['year'], f['payment_type_id']

    paid_qs = Payment.objects.filter(
        period_month=month, period_year=year, member__isnull=False,
    )
    if pt_id:
        paid_qs = paid_qs.filter(payment_type_id=pt_id)
    paid_ids = paid_qs.values_list('member_id', flat=True)

    unpaid = list(Member.objects.filter(is_active=True).exclude(
        pk__in=paid_ids).select_related('lingkungan__wilayah'))

    if pt_id:
        try:
            pt_name = PaymentType.objects.get(pk=pt_id).name
        except PaymentType.DoesNotExist:
            pt_name = 'Semua'
    else:
        pt_name = 'Semua'
    buf = build_unpaid_excel(unpaid, month, year, pt_name)
    response = HttpResponse(buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="belum-bayar-{month}-{year}.xlsx"'
    return response
