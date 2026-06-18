from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count
from members.models import Member, Wilayah, Lingkungan
from payments.models import Payment, PaymentType
from .exporters import build_monthly_excel, build_annual_excel, build_unpaid_excel


def _get_filter_context(request):
    now = timezone.localtime(timezone.now())
    return {
        'month': int(request.GET.get('month', now.month)),
        'year': int(request.GET.get('year', now.year)),
        'payment_type_id': request.GET.get('payment_type', ''),
        'wilayah_id': request.GET.get('wilayah', ''),
        'lingkungan_id': request.GET.get('lingkungan', ''),
        'now': now,
    }


@login_required
def report_index(request):
    return render(request, 'reports/index.html', {
        'payment_types': PaymentType.objects.filter(is_active=True),
        'wilayah_list': Wilayah.objects.all(),
        'years': range(timezone.now().year - 3, timezone.now().year + 2),
        'months': range(1, 13),
    })


@login_required
def monthly_report(request):
    f = _get_filter_context(request)
    qs = Payment.objects.filter(
        period_month=f['month'], period_year=f['year']
    ).select_related('member__lingkungan__wilayah', 'payment_type', 'recorded_by')

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

    monthly_totals = []
    for m in range(1, 13):
        total = Payment.objects.filter(period_month=m, period_year=year).aggregate(
            t=Sum('amount'))['t'] or 0
        count = Payment.objects.filter(period_month=m, period_year=year).count()
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

    paid_member_ids = Payment.objects.filter(
        period_month=month, period_year=year
    )
    if pt_id:
        paid_member_ids = paid_member_ids.filter(payment_type_id=pt_id)
    paid_member_ids = paid_member_ids.values_list('member_id', flat=True)

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
        period_month=f['month'], period_year=f['year']
    ).select_related('member__lingkungan__wilayah', 'payment_type', 'recorded_by'))
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
    monthly_totals = []
    for m in range(1, 13):
        total = Payment.objects.filter(period_month=m, period_year=year).aggregate(
            t=Sum('amount'))['t'] or 0
        count = Payment.objects.filter(period_month=m, period_year=year).count()
        monthly_totals.append([m, float(total), count])

    members = Member.objects.filter(is_active=True).select_related('lingkungan__wilayah')
    member_summary = []
    for mem in members:
        payments = Payment.objects.filter(member=mem, period_year=year)
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
def export_unpaid(request):
    f = _get_filter_context(request)
    month, year, pt_id = f['month'], f['year'], f['payment_type_id']

    paid_ids = Payment.objects.filter(period_month=month, period_year=year)
    if pt_id:
        paid_ids = paid_ids.filter(payment_type_id=pt_id)
    paid_ids = paid_ids.values_list('member_id', flat=True)

    unpaid = list(Member.objects.filter(is_active=True).exclude(
        pk__in=paid_ids).select_related('lingkungan__wilayah'))

    pt_name = PaymentType.objects.get(pk=pt_id).name if pt_id else 'Semua'
    buf = build_unpaid_excel(unpaid, month, year, pt_name)
    response = HttpResponse(buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="belum-bayar-{month}-{year}.xlsx"'
    return response
