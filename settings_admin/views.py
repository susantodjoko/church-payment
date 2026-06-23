import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from church_payment.mixins import SuperAdminRequired
from members.models import Wilayah, Lingkungan, Keluarga
from payments.models import PaymentType
from .forms import UserCreateForm, WilayahForm, LingkunganForm, PaymentTypeForm, KeluargaForm
from settings_admin.csv_utils import parse_anggota_csv


class UserListView(SuperAdminRequired, View):
    def get(self, request):
        users = User.objects.prefetch_related('groups').order_by('username')
        return render(request, 'settings_admin/users.html', {
            'users': users, 'form': UserCreateForm()
        })

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pengguna berhasil ditambahkan.')
            return redirect('settings_users')
        users = User.objects.prefetch_related('groups').order_by('username')
        return render(request, 'settings_admin/users.html', {'users': users, 'form': form})


class WilayahListView(SuperAdminRequired, View):
    def get(self, request):
        return render(request, 'settings_admin/areas.html', {
            'wilayah_list': Wilayah.objects.all(),
            'lingkungan_list': Lingkungan.objects.select_related('wilayah').all(),
            'wilayah_form': WilayahForm(),
            'lingkungan_form': LingkunganForm(),
        })

    def post(self, request):
        if 'add_wilayah' in request.POST:
            form = WilayahForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Wilayah ditambahkan.')
        elif 'add_lingkungan' in request.POST:
            form = LingkunganForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Lingkungan ditambahkan.')
        return redirect('settings_wilayah')


class PaymentTypeListView(SuperAdminRequired, View):
    def get(self, request):
        return render(request, 'settings_admin/payment_types.html', {
            'payment_types': PaymentType.objects.all(),
            'form': PaymentTypeForm(),
        })

    def post(self, request):
        form = PaymentTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Jenis pembayaran ditambahkan.')
            return redirect('settings_payment_types')
        return render(request, 'settings_admin/payment_types.html', {
            'payment_types': PaymentType.objects.all(), 'form': form
        })


class KeluargaToggleActiveView(SuperAdminRequired, View):
    def post(self, request, pk):
        kk = get_object_or_404(Keluarga, pk=pk)
        kk.is_active = not kk.is_active
        kk.save(update_fields=['is_active'])
        status = 'diaktifkan' if kk.is_active else 'dinonaktifkan'
        messages.success(request, f'{kk.name} berhasil {status}.')
        return redirect('settings_keluarga')


class KeluargaListView(SuperAdminRequired, View):
    def get(self, request):
        return render(request, 'settings_admin/keluarga.html', {
            'keluarga_list': Keluarga.objects.select_related('lingkungan__wilayah').all(),
            'form': KeluargaForm(),
        })

    def post(self, request):
        form = KeluargaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Keluarga berhasil ditambahkan.')
            return redirect('settings_keluarga')
        return render(request, 'settings_admin/keluarga.html', {
            'keluarga_list': Keluarga.objects.select_related('lingkungan__wilayah').all(),
            'form': form,
        })


@login_required
def download_anggota_template(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='Super Admin').exists()):
        raise PermissionDenied

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="template_anggota.csv"'
    writer = csv.writer(response)
    writer.writerow(['member_id', 'full_name', 'gender', 'join_date', 'lingkungan',
                     'date_of_birth', 'phone', 'address', 'keluarga_kk'])
    writer.writerow(['BML001', 'Budi Santoso', 'M', '2024-01-15', 'St. Maria',
                     '1990-05-10', '08123456789', 'Jl. Contoh No. 1', ''])
    writer.writerow(['BML002', 'Sari Dewi', 'F', '2024-02-20', 'St. Yoseph',
                     '', '08987654321', '', ''])
    return response


class UploadAnggotaView(SuperAdminRequired, View):
    SESSION_KEY = 'upload_anggota_preview'

    def get(self, request):
        return render(request, 'settings_admin/upload_anggota.html')

    def post(self, request):
        action = request.POST.get('action', 'preview')
        if action == 'confirm':
            return self._confirm(request)
        return self._preview(request)

    def _preview(self, request):
        uploaded = request.FILES.get('csv_file')
        if not uploaded:
            messages.error(request, 'Pilih file CSV terlebih dahulu.')
            return render(request, 'settings_admin/upload_anggota.html')

        if not uploaded.name.lower().endswith('.csv'):
            messages.error(request, 'File harus berformat CSV (.csv).')
            return render(request, 'settings_admin/upload_anggota.html')

        try:
            rows = parse_anggota_csv(uploaded)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, 'settings_admin/upload_anggota.html')

        if not rows:
            messages.warning(request, 'File CSV tidak memiliki baris data.')
            return render(request, 'settings_admin/upload_anggota.html')

        request.session[self.SESSION_KEY] = rows

        valid = sum(1 for r in rows if r['status'] == 'valid')
        conflicts = sum(1 for r in rows if r['status'] == 'conflict')
        errors = sum(1 for r in rows if r['status'] == 'error')

        return render(request, 'settings_admin/upload_anggota.html', {
            'rows': rows,
            'valid_count': valid,
            'conflict_count': conflicts,
            'error_count': errors,
            'has_valid': valid > 0,
        })

    def _confirm(self, request):
        # implemented in Task 4
        return render(request, 'settings_admin/upload_anggota.html')
