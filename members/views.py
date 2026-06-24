from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.db import models
from church_payment.mixins import SuperAdminRequired
from .models import Member, Wilayah, Lingkungan, Keluarga
from .forms import MemberForm


@login_required
def member_list(request):
    show_inactive = request.GET.get('show_inactive') == '1'
    qs = Member.objects.select_related('lingkungan__wilayah')
    if not show_inactive:
        qs = qs.filter(is_active=True)
    q = request.GET.get('q', '')
    wilayah_id = request.GET.get('wilayah', '')
    lingkungan_id = request.GET.get('lingkungan', '')

    if q:
        qs = qs.filter(
            models.Q(full_name__icontains=q) |
            models.Q(member_id__icontains=q) |
            models.Q(keluarga__kk_number__icontains=q) |
            models.Q(keluarga__name__icontains=q)
        )
    if wilayah_id:
        qs = qs.filter(lingkungan__wilayah_id=wilayah_id)
    if lingkungan_id:
        qs = qs.filter(lingkungan_id=lingkungan_id)

    return render(request, 'members/list.html', {
        'members': qs,
        'wilayah_list': Wilayah.objects.all(),
        'lingkungan_list': Lingkungan.objects.select_related('wilayah').all(),
        'q': q,
        'show_inactive': show_inactive,
    })


@login_required
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    payments = member.payments.select_related('payment_type', 'recorded_by').order_by('-period_year', '-period_month')
    return render(request, 'members/detail.html', {'member': member, 'payments': payments})


def member_search(request):
    """HTMX partial: returns search results dropdown for Record Payment page."""
    if not request.user.is_authenticated:
        return HttpResponse('<p class="text-muted small mt-1">Sesi berakhir, silakan login ulang.</p>', status=200)
    q = request.GET.get('q', '').strip()
    members = []
    if len(q) >= 2:
        members = Member.objects.filter(
            models.Q(full_name__icontains=q) | models.Q(member_id__icontains=q),
            is_active=True,
        ).select_related('lingkungan')[:10]
    return render(request, 'members/partials/search_results.html', {'members': members, 'q': q})


class MemberToggleActiveView(SuperAdminRequired, View):
    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        member.is_active = not member.is_active
        member.save(update_fields=['is_active'])
        status = 'diaktifkan' if member.is_active else 'dinonaktifkan'
        messages.success(request, f'{member.full_name} berhasil {status}.')
        return redirect('member_list')


class MemberCreateView(SuperAdminRequired, View):
    def get(self, request):
        return render(request, 'members/form.html', {'form': MemberForm(), 'action': 'Tambah'})

    def post(self, request):
        form = MemberForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Anggota berhasil ditambahkan.')
            return redirect('member_list')
        return render(request, 'members/form.html', {'form': form, 'action': 'Tambah'})


class MemberUpdateView(SuperAdminRequired, View):
    def get(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        return render(request, 'members/form.html', {'form': MemberForm(instance=member), 'action': 'Edit', 'member': member})

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data anggota diperbarui.')
            return redirect('member_detail', pk=pk)
        return render(request, 'members/form.html', {'form': form, 'action': 'Edit', 'member': member})


@login_required
def keluarga_options(request):
    """HTMX partial: <select> options for KK filtered by lingkungan (used on member form)."""
    lingkungan_id = request.GET.get('lingkungan', '')
    results = []
    if lingkungan_id:
        results = Keluarga.objects.filter(
            lingkungan_id=lingkungan_id, is_active=True
        ).order_by('kk_number')
    return render(request, 'members/partials/keluarga_options.html', {'results': results})


def keluarga_search(request):
    """HTMX partial: returns KK search results for Record Payment page."""
    if not request.user.is_authenticated:
        return HttpResponse('<p class="text-muted small mt-1">Sesi berakhir, silakan login ulang.</p>', status=200)
    q = request.GET.get('q', '').strip()
    results = []
    if len(q) >= 2:
        results = Keluarga.objects.filter(
            models.Q(kk_number__icontains=q) | models.Q(name__icontains=q),
            is_active=True
        ).select_related('lingkungan')[:10]
    return render(request, 'members/partials/keluarga_search_results.html', {'results': results, 'q': q})
