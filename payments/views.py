from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from members.models import Member, Wilayah, Lingkungan
from .models import Payment, PaymentType
from .forms import PaymentForm


@login_required
def record_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        member_id = request.POST.get('member_id')
        if form.is_valid() and member_id:
            try:
                member = Member.objects.get(pk=member_id)
            except Member.DoesNotExist:
                messages.error(request, 'Anggota tidak ditemukan.')
                return render(request, 'payments/new.html', {'form': form})
            payment = form.save(commit=False)
            payment.member = member
            payment.recorded_by = request.user
            duplicate = Payment.objects.filter(
                member=member,
                payment_type=payment.payment_type,
                period_month=payment.period_month,
                period_year=payment.period_year,
            ).exists()
            if duplicate:
                messages.error(
                    request,
                    f'Pembayaran {payment.payment_type} untuk {member.full_name} '
                    f'periode {payment.period_month}/{payment.period_year} sudah pernah dicatat.'
                )
                return render(request, 'payments/new.html', {'form': form})
            payment.save()
            messages.success(request, f'Pembayaran untuk {member.full_name} berhasil dicatat.')
            return redirect('payment_list')
        else:
            messages.error(request, 'Periksa kembali data yang dimasukkan.')
    else:
        form = PaymentForm()

    prefill_member = None
    if request.method == 'GET' and request.GET.get('member_id'):
        try:
            prefill_member = Member.objects.get(pk=request.GET.get('member_id'))
        except Member.DoesNotExist:
            pass

    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member})


@login_required
def payment_list(request):
    now = timezone.localtime(timezone.now())
    month = int(request.GET.get('month', now.month))
    year = int(request.GET.get('year', now.year))
    payment_type_id = request.GET.get('payment_type', '')
    wilayah_id = request.GET.get('wilayah', '')
    lingkungan_id = request.GET.get('lingkungan', '')

    qs = Payment.objects.filter(
        period_month=month, period_year=year
    ).select_related('member__lingkungan__wilayah', 'payment_type', 'recorded_by')

    if payment_type_id:
        qs = qs.filter(payment_type_id=payment_type_id)
    if wilayah_id:
        qs = qs.filter(member__lingkungan__wilayah_id=wilayah_id)
    if lingkungan_id:
        qs = qs.filter(member__lingkungan_id=lingkungan_id)

    context = {
        'payments': qs,
        'month': month, 'year': year,
        'payment_types': PaymentType.objects.filter(is_active=True),
        'wilayah_list': Wilayah.objects.all(),
        'lingkungan_list': Lingkungan.objects.select_related('wilayah').all(),
        'selected_payment_type': payment_type_id,
        'months': range(1, 13),
        'years': range(now.year - 2, now.year + 2),
    }

    if request.htmx:
        return render(request, 'payments/partials/payment_table.html', context)
    return render(request, 'payments/list.html', context)
