from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from church_payment.mixins import SuperAdminRequired
from members.models import Wilayah, Lingkungan, Keluarga
from payments.models import PaymentType
from .forms import UserCreateForm, WilayahForm, LingkunganForm, PaymentTypeForm, KeluargaForm


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
