from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.shortcuts import render, redirect
from django.utils import timezone
from members.models import Member, Wilayah, Lingkungan, Keluarga
from .models import Payment, PaymentType
from .forms import PaymentForm, PKSS_TYPE_NAME, KARTU_KUNING_TYPE_NAME


@login_required
def record_payment(request):
    prefill_member = None
    if request.method == 'GET' and request.GET.get('member_id'):
        try:
            prefill_member = Member.objects.get(pk=request.GET.get('member_id'))
        except Member.DoesNotExist:
            pass

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment_type_name = payment.payment_type.name

            if payment_type_name == PKSS_TYPE_NAME:
                member_id = request.POST.get('member_id')
                if not member_id:
                    messages.error(request, 'Pilih anggota terlebih dahulu.')
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member})
                try:
                    member = Member.objects.get(pk=member_id)
                except Member.DoesNotExist:
                    messages.error(request, 'Anggota tidak ditemukan.')
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member})
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
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member})
                payment.member = member
                payment.keluarga = None
                subject_name = member.full_name

            elif payment_type_name == KARTU_KUNING_TYPE_NAME:
                keluarga_id = request.POST.get('keluarga_id')
                if not keluarga_id:
                    messages.error(request, 'Pilih Keluarga (KK) terlebih dahulu.')
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member})
                try:
                    keluarga = Keluarga.objects.get(pk=keluarga_id)
                except Keluarga.DoesNotExist:
                    messages.error(request, 'Keluarga tidak ditemukan.')
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member})
                duplicate = Payment.objects.filter(
                    keluarga=keluarga,
                    payment_type=payment.payment_type,
                    period_month=payment.period_month,
                    period_year=payment.period_year,
                ).exists()
                if duplicate:
                    messages.error(
                        request,
                        f'Pembayaran {payment.payment_type} untuk {keluarga} '
                        f'periode {payment.period_month}/{payment.period_year} sudah pernah dicatat.'
                    )
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member})
                payment.keluarga = keluarga
                payment.member = None
                subject_name = str(keluarga)
            else:
                messages.error(request, 'Jenis pembayaran tidak valid.')
                return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member})

            payment.recorded_by = request.user
            payment.save()
            messages.success(request, f'Pembayaran untuk {subject_name} berhasil dicatat.')
            return redirect('payment_list')
        else:
            messages.error(request, 'Periksa kembali data yang dimasukkan.')
    else:
        form = PaymentForm()

    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member})


@login_required
def payment_list(request):
    now = timezone.localtime(timezone.now())
    month = int(request.GET.get('month', now.month))
    year = int(request.GET.get('year', now.year))
    payment_type_id = request.GET.get('payment_type', '')
    wilayah_id = request.GET.get('wilayah', '')
    lingkungan_id = request.GET.get('lingkungan', '')
    tab = request.GET.get('tab', 'belum')  # 'belum' or 'sudah'

    qs = Payment.objects.filter(
        period_month=month, period_year=year,
        recorded_by=request.user,
    ).select_related('member__lingkungan__wilayah', 'keluarga__lingkungan', 'payment_type', 'recorded_by')

    if payment_type_id:
        qs = qs.filter(payment_type_id=payment_type_id)
    if wilayah_id:
        qs = qs.filter(
            models.Q(member__lingkungan__wilayah_id=wilayah_id) |
            models.Q(keluarga__lingkungan__wilayah_id=wilayah_id)
        )
    if lingkungan_id:
        qs = qs.filter(
            models.Q(member__lingkungan_id=lingkungan_id) |
            models.Q(keluarga__lingkungan_id=lingkungan_id)
        )

    if tab == 'sudah':
        payments = qs.filter(date_reported__isnull=False)
    else:
        payments = qs.filter(date_reported__isnull=True)

    context = {
        'payments': payments,
        'month': month, 'year': year, 'tab': tab,
        'payment_types': PaymentType.objects.filter(is_active=True),
        'wilayah_list': Wilayah.objects.all(),
        'lingkungan_list': Lingkungan.objects.select_related('wilayah').all(),
        'selected_payment_type': payment_type_id,
        'selected_wilayah': wilayah_id,
        'months': range(1, 13),
        'years': range(now.year - 2, now.year + 2),
    }

    if request.htmx:
        return render(request, 'payments/partials/payment_table.html', context)
    return render(request, 'payments/list.html', context)


@login_required
def batch_report(request):
    if request.method != 'POST':
        return redirect('payment_list')
    payment_ids = request.POST.getlist('payment_ids')
    if not payment_ids:
        messages.error(request, 'Pilih minimal satu pembayaran untuk dilaporkan.')
        return redirect('payment_list')
    now = timezone.now()
    updated = Payment.objects.filter(
        pk__in=payment_ids,
        recorded_by=request.user,
        date_reported__isnull=True,
    ).update(date_reported=now)
    messages.success(request, f'{updated} pembayaran berhasil dilaporkan ke Bendahara Utama.')
    return redirect('payment_list')
