from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import models
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View
from church_payment.mixins import SuperAdminRequired
from members.models import Member, Wilayah, Lingkungan, Keluarga
from .models import Payment, PaymentType
from .forms import PaymentForm, PKSS_TYPE_NAME, KARTU_KUNING_TYPE_NAME


@login_required
def record_payment(request):
    prefill_member = None
    prefill_payment_type_id = ''
    prefill_month = ''
    prefill_year = ''

    pkss_type = PaymentType.objects.filter(name=PKSS_TYPE_NAME, is_active=True).first()
    pkss_type_id = pkss_type.pk if pkss_type else ''

    if request.method == 'GET':
        if request.GET.get('member_id'):
            try:
                prefill_member = Member.objects.get(pk=request.GET.get('member_id'))
            except Member.DoesNotExist:
                pass
        prefill_payment_type_id = request.GET.get('payment_type_id', '')
        prefill_month = request.GET.get('month', '')
        prefill_year = request.GET.get('year', '')

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment_type_name = payment.payment_type.name

            if payment_type_name == PKSS_TYPE_NAME:
                member_id = request.POST.get('member_id')
                if not member_id:
                    messages.error(request, 'Pilih anggota terlebih dahulu.')
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member, 'pkss_type_id': pkss_type_id})
                try:
                    member = Member.objects.get(pk=member_id)
                except Member.DoesNotExist:
                    messages.error(request, 'Anggota tidak ditemukan.')
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member, 'pkss_type_id': pkss_type_id})
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
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member, 'pkss_type_id': pkss_type_id})
                payment.member = member
                payment.keluarga = None
                subject_name = member.full_name

            elif payment_type_name == KARTU_KUNING_TYPE_NAME:
                keluarga_id = request.POST.get('keluarga_id')
                if not keluarga_id:
                    messages.error(request, 'Pilih Keluarga (KK) terlebih dahulu.')
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member, 'pkss_type_id': pkss_type_id})
                try:
                    keluarga = Keluarga.objects.get(pk=keluarga_id)
                except Keluarga.DoesNotExist:
                    messages.error(request, 'Keluarga tidak ditemukan.')
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member, 'pkss_type_id': pkss_type_id})
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
                    return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member, 'pkss_type_id': pkss_type_id})
                payment.keluarga = keluarga
                payment.member = None
                subject_name = str(keluarga)
            else:
                messages.error(request, 'Jenis pembayaran tidak valid.')
                return render(request, 'payments/new.html', {'form': form, 'prefill_member': prefill_member, 'pkss_type_id': pkss_type_id})

            payment.recorded_by = request.user
            payment.save()
            messages.success(request, f'Pembayaran untuk {subject_name} berhasil dicatat.')
            return redirect('payment_list')
        else:
            messages.error(request, 'Periksa kembali data yang dimasukkan.')
    else:
        form = PaymentForm()

    return render(request, 'payments/new.html', {
        'form': form,
        'prefill_member': prefill_member,
        'prefill_payment_type_id': prefill_payment_type_id,
        'prefill_month': prefill_month,
        'prefill_year': prefill_year,
        'pkss_type_id': pkss_type_id,
    })


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


class LaporanMasukView(SuperAdminRequired, View):
    def get(self, request):
        # Group unconfirmed payments by (recorded_by, date_reported date)
        pending = Payment.objects.filter(
            date_reported__isnull=False,
            date_confirmed__isnull=True,
        ).select_related(
            'member__lingkungan', 'keluarga__lingkungan',
            'payment_type', 'recorded_by'
        ).order_by('recorded_by__username', 'date_reported')

        # Group into batches: (treasurer, date_reported_date) → [payments]
        batches = {}
        for p in pending:
            key = (p.recorded_by, p.date_reported.date())
            batches.setdefault(key, []).append(p)

        return render(request, 'payments/laporan_masuk.html', {
            'batches': [
                {
                    'treasurer': k[0],
                    'date_reported': k[1],
                    'payments': v,
                    'total': sum(p.amount for p in v),
                }
                for k, v in batches.items()
            ]
        })


@login_required
def confirm_laporan(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='Super Admin').exists()):
        raise PermissionDenied
    if request.method != 'POST':
        return redirect('laporan_masuk')
    payment_ids = request.POST.getlist('payment_ids')
    if not payment_ids:
        messages.error(request, 'Tidak ada pembayaran yang dipilih.')
        return redirect('laporan_masuk')
    now = timezone.now()
    updated = Payment.objects.filter(
        pk__in=payment_ids,
        date_reported__isnull=False,
        date_confirmed__isnull=True,
    ).update(date_confirmed=now, confirmed_by=request.user)
    messages.success(request, f'{updated} pembayaran berhasil dikonfirmasi.')
    return redirect('laporan_masuk')
