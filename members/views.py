from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from church_payment.mixins import SuperAdminRequired
from .models import Member, Wilayah, Lingkungan
from .forms import MemberForm


@login_required
def member_list(request):
    qs = Member.objects.select_related('lingkungan__wilayah').filter(is_active=True)
    q = request.GET.get('q', '')
    wilayah_id = request.GET.get('wilayah', '')
    lingkungan_id = request.GET.get('lingkungan', '')

    if q:
        qs = qs.filter(full_name__icontains=q)
    if wilayah_id:
        qs = qs.filter(lingkungan__wilayah_id=wilayah_id)
    if lingkungan_id:
        qs = qs.filter(lingkungan_id=lingkungan_id)

    return render(request, 'members/list.html', {
        'members': qs,
        'wilayah_list': Wilayah.objects.all(),
        'lingkungan_list': Lingkungan.objects.select_related('wilayah').all(),
        'q': q,
    })


@login_required
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    payments = member.payments.select_related('payment_type', 'recorded_by').order_by('-period_year', '-period_month')
    return render(request, 'members/detail.html', {'member': member, 'payments': payments})


@login_required
def member_search(request):
    """HTMX partial: returns search results dropdown for Record Payment page."""
    q = request.GET.get('q', '').strip()
    members = []
    if len(q) >= 2:
        members = Member.objects.filter(
            full_name__icontains=q, is_active=True
        ).select_related('lingkungan')[:10]
    return render(request, 'members/partials/search_results.html', {'members': members, 'q': q})


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
