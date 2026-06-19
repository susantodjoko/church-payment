# Payment Workflow Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Keluarga (KK) model, two payment types (Iuran PKSS / Iuran Kartu Kuning), two-stage reporting workflow (date_received → date_reported → date_confirmed), and Laporan Masuk confirmation page for Super Admin.

**Architecture:** Extend existing Payment model with new fields and a new Keluarga model in the members app. Dynamic payment form switches between member search and KK dropdown based on payment type. Batch report action stamps date_reported; Super Admin confirmation page stamps date_confirmed.

**Tech Stack:** Django 4.x, HTMX 1.9, Bootstrap 5.3, SQLite (dev) / PostgreSQL (prod), openpyxl

## Global Constraints

- Python/Django patterns already in use: function-based views with `@login_required`, class-based views with `SuperAdminRequired` mixin
- All templates extend `base.html`; HTMX partials are standalone HTML fragments
- IDR currency: use `|idr` custom filter from `payments/templatetags/idr_filters.py`
- All amounts: `DecimalField(max_digits=10, decimal_places=2)`
- Duplicate payment guard: check before save in view, not model
- `date_reported` and `date_confirmed` are always set by the system, never user-entered
- Two payment types only: "Iuran PKSS" (per member) and "Iuran Kartu Kuning" (per KK)
- Run migrations with: `python manage.py makemigrations && python manage.py migrate`

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `members/models.py` | Modify | Add Keluarga model |
| `members/views.py` | Modify | Add keluarga_search HTMX view |
| `members/urls.py` | Modify | Add keluarga search URL |
| `members/templates/members/partials/keluarga_search_results.html` | Create | HTMX dropdown for KK search |
| `payments/models.py` | Modify | Rename date_paid→date_received, make member nullable, add keluarga/date_reported/date_confirmed/confirmed_by |
| `payments/forms.py` | Modify | Dynamic form: member search vs KK dropdown per payment type |
| `payments/views.py` | Modify | Update record_payment, payment_list (tabs), add batch_report, laporan_masuk, confirm_laporan |
| `payments/urls.py` | Modify | Add batch_report, laporan_masuk, confirm_laporan URLs |
| `payments/templates/payments/new.html` | Modify | Dynamic member/KK field with JS toggle |
| `payments/templates/payments/list.html` | Modify | Two tabs + batch report form |
| `payments/templates/payments/partials/payment_table.html` | Modify | Add checkbox, date_received column, status badge |
| `payments/templates/payments/laporan_masuk.html` | Create | Super Admin confirmation page |
| `settings_admin/forms.py` | Modify | Add KeluargaForm |
| `settings_admin/views.py` | Modify | Add KeluargaListView |
| `settings_admin/urls.py` | Modify | Add keluarga URL |
| `settings_admin/templates/settings_admin/keluarga.html` | Create | KK management page |
| `templates/base.html` | Modify | Add Laporan Masuk link for Super Admin |
| `members/templates/members/detail.html` | Modify | Handle nullable member on payments |
| `reports/views.py` | Modify | Rename date_paid→date_received references |
| `reports/exporters.py` | Modify | Rename date_paid→date_received references |

---

## Task 1: Keluarga Model + Migration

**Files:**
- Modify: `members/models.py`
- Run: `python manage.py makemigrations members`

**Interfaces:**
- Produces: `Keluarga` model with fields `kk_number`, `name`, `lingkungan`, `is_active`; importable as `from members.models import Keluarga`

- [ ] **Step 1: Add Keluarga to members/models.py**

Open `members/models.py` and add this class after the `Lingkungan` class (before `Member`):

```python
class Keluarga(models.Model):
    kk_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    lingkungan = models.ForeignKey(Lingkungan, on_delete=models.PROTECT, related_name='keluarga_set')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['lingkungan__name', 'kk_number']
        verbose_name_plural = 'Keluarga'

    def __str__(self):
        return f'{self.kk_number} — {self.name}'
```

- [ ] **Step 2: Generate migration**

```bash
python manage.py makemigrations members
```

Expected output: `Migrations for 'members': members/migrations/000X_keluarga.py — Create model Keluarga`

- [ ] **Step 3: Apply migration**

```bash
python manage.py migrate
```

Expected: `Applying members.000X_keluarga... OK`

- [ ] **Step 4: Verify in shell**

```bash
python manage.py shell -c "from members.models import Keluarga; print(Keluarga._meta.fields)"
```

Expected: lists `id`, `kk_number`, `name`, `lingkungan`, `is_active`

- [ ] **Step 5: Commit**

```bash
git add members/models.py members/migrations/
git commit -m "feat: add Keluarga model to members app"
```

---

## Task 2: Update Payment Model + Migration

**Files:**
- Modify: `payments/models.py`
- Run: `python manage.py makemigrations payments`

**Interfaces:**
- Produces: `Payment` model with `date_received` (replaces `date_paid`), nullable `member`, `keluarga` FK, `date_reported`, `date_confirmed`, `confirmed_by`
- `Payment.is_reported` property: returns `True` if `date_reported` is not None
- `Payment.is_confirmed` property: returns `True` if `date_confirmed` is not None

- [ ] **Step 1: Rewrite payments/models.py**

Replace the entire file content with:

```python
from django.db import models
from django.contrib.auth.models import User


class PaymentType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Payment(models.Model):
    member = models.ForeignKey(
        'members.Member', on_delete=models.PROTECT,
        related_name='payments', null=True, blank=True
    )
    keluarga = models.ForeignKey(
        'members.Keluarga', on_delete=models.PROTECT,
        related_name='payments', null=True, blank=True
    )
    payment_type = models.ForeignKey(PaymentType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_received = models.DateTimeField()
    period_month = models.IntegerField()
    period_year = models.IntegerField()
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='recorded_payments')
    notes = models.TextField(null=True, blank=True)
    date_reported = models.DateTimeField(null=True, blank=True)
    date_confirmed = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True, related_name='confirmed_payments'
    )

    class Meta:
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        subject = self.member.full_name if self.member else str(self.keluarga)
        return f'{subject} — {self.period_month}/{self.period_year}'

    @property
    def is_reported(self):
        return self.date_reported is not None

    @property
    def is_confirmed(self):
        return self.date_confirmed is not None
```

- [ ] **Step 2: Generate migration**

```bash
python manage.py makemigrations payments
```

Django will detect: rename `date_paid`→`date_received`, add `keluarga`, make `member` nullable, add `date_reported`, `date_confirmed`, `confirmed_by`. When prompted about renaming `date_paid` to `date_received`, answer **y**.

- [ ] **Step 3: Apply migration**

```bash
python manage.py migrate
```

Expected: `Applying payments.000X_update_payment... OK`

- [ ] **Step 4: Verify in shell**

```bash
python manage.py shell -c "from payments.models import Payment; p = Payment.__dict__; print([f for f in p if not f.startswith('_')])"
```

Expected: includes `date_received`, `keluarga`, `date_reported`, `date_confirmed`, `confirmed_by`

- [ ] **Step 5: Commit**

```bash
git add payments/models.py payments/migrations/
git commit -m "feat: update Payment model -- date_received, keluarga FK, reporting fields"
```

---

## Task 3: Update PaymentForm + Record Payment View

**Files:**
- Modify: `payments/forms.py`
- Modify: `payments/views.py`
- Modify: `payments/templates/payments/new.html`
- Create: `members/templates/members/partials/keluarga_search_results.html`
- Modify: `members/views.py` (add keluarga_search)
- Modify: `members/urls.py` (add keluarga search URL)

**Interfaces:**
- Consumes: `Keluarga` from `members.models`, `Payment` with new fields from Task 2
- Produces: `record_payment` view at `/payments/new/` that handles both PKSS (member) and Kartu Kuning (KK) payments

- [ ] **Step 1: Add keluarga_search view to members/views.py**

Add this function at the end of `members/views.py`:

```python
@login_required
def keluarga_search(request):
    """HTMX partial: returns KK search results for Record Payment page."""
    q = request.GET.get('q', '').strip()
    results = []
    if len(q) >= 2:
        results = Keluarga.objects.filter(
            models.Q(kk_number__icontains=q) | models.Q(name__icontains=q),
            is_active=True
        ).select_related('lingkungan')[:10]
    return render(request, 'members/partials/keluarga_search_results.html', {'results': results, 'q': q})
```

Also add these imports at the top of `members/views.py`:

```python
from django.db import models
from .models import Member, Wilayah, Lingkungan, Keluarga
```

- [ ] **Step 2: Add keluarga search URL to members/urls.py**

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.member_list, name='member_list'),
    path('search/', views.member_search, name='member_search'),
    path('keluarga/search/', views.keluarga_search, name='keluarga_search'),
    path('new/', views.MemberCreateView.as_view(), name='member_create'),
    path('<int:pk>/', views.member_detail, name='member_detail'),
    path('<int:pk>/edit/', views.MemberUpdateView.as_view(), name='member_update'),
]
```

- [ ] **Step 3: Create keluarga search results partial**

Create `members/templates/members/partials/keluarga_search_results.html`:

```html
{% if results %}
<ul class="list-group position-absolute w-100" style="z-index:1000;top:100%">
  {% for kk in results %}
  <li class="list-group-item list-group-item-action" style="cursor:pointer"
      onclick="selectKeluarga('{{ kk.pk }}', '{{ kk.kk_number }} — {{ kk.name }}')">
    <strong>{{ kk.kk_number }}</strong> — {{ kk.name }}
    <small class="text-muted d-block">{{ kk.lingkungan }}</small>
  </li>
  {% endfor %}
</ul>
{% elif q|length >= 2 %}
<div class="text-muted small mt-1">KK tidak ditemukan.</div>
{% endif %}
```

- [ ] **Step 4: Rewrite payments/forms.py**

Replace the entire file with:

```python
from django import forms
from django.core.validators import MinValueValidator
from django.utils import timezone
from members.models import Keluarga
from .models import Payment, PaymentType

PKSS_TYPE_NAME = 'Iuran PKSS'
KARTU_KUNING_TYPE_NAME = 'Iuran Kartu Kuning'


class PaymentForm(forms.ModelForm):
    member_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    member_display = forms.CharField(
        label='Anggota',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ketik nama anggota...',
            'autocomplete': 'off',
            'hx-get': '/members/search/',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#member-search-results',
            'hx-indicator': '#member-search-spinner',
            'name': 'q',
        })
    )
    keluarga_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    keluarga_display = forms.CharField(
        label='Keluarga (KK)',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ketik nomor atau nama KK...',
            'autocomplete': 'off',
            'hx-get': '/members/keluarga/search/',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#keluarga-search-results',
            'hx-indicator': '#keluarga-search-spinner',
            'name': 'q',
        })
    )

    class Meta:
        model = Payment
        fields = ['payment_type', 'amount', 'date_received', 'period_month', 'period_year', 'notes']
        widgets = {
            'date_received': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'payment_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_payment_type'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000'}),
            'period_month': forms.Select(choices=[(i, i) for i in range(1, 13)], attrs={'class': 'form-select'}),
            'period_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Opsional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_type'].queryset = PaymentType.objects.filter(is_active=True)
        now = timezone.localtime(timezone.now())
        self.fields['date_received'].initial = now.strftime('%Y-%m-%dT%H:%M')
        self.fields['period_month'].initial = now.month
        self.fields['period_year'].initial = now.year
        self.fields['notes'].required = False
        self.fields['amount'].validators.append(MinValueValidator(1))
```

- [ ] **Step 5: Rewrite payments/views.py record_payment view**

Replace the `record_payment` function in `payments/views.py` with:

```python
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from members.models import Member, Wilayah, Lingkungan
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
                    from members.models import Keluarga
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
```

- [ ] **Step 6: Rewrite payments/templates/payments/new.html**

Replace the entire file with:

```html
{% extends 'base.html' %}
{% block title %}Catat Pembayaran{% endblock %}
{% block content %}
<h3>Catat Pembayaran</h3>
<form method="post" class="mt-3" style="max-width:600px">
  {% csrf_token %}
  <input type="hidden" name="member_id" id="member-id-hidden" value="">
  <input type="hidden" name="keluarga_id" id="keluarga-id-hidden" value="">

  <div class="mb-3">
    <label class="form-label">Jenis Pembayaran *</label>
    {{ form.payment_type }}
  </div>

  <div class="mb-3 position-relative" id="member-field">
    <label class="form-label">Anggota *</label>
    <div class="position-relative">
      <input type="text" id="member-search-input" class="form-control"
             placeholder="Ketik nama anggota..."
             autocomplete="off"
             hx-get="/members/search/"
             hx-trigger="keyup changed delay:300ms"
             hx-target="#member-search-results"
             hx-indicator="#member-search-spinner"
             name="q">
      <span id="member-search-spinner" class="htmx-indicator spinner-border spinner-border-sm text-secondary position-absolute"
            style="right:10px;top:10px" role="status"></span>
    </div>
    <div id="member-search-results" class="position-relative"></div>
  </div>

  <div class="mb-3 position-relative" id="keluarga-field" style="display:none">
    <label class="form-label">Keluarga (KK) *</label>
    <div class="position-relative">
      <input type="text" id="keluarga-search-input" class="form-control"
             placeholder="Ketik nomor atau nama KK..."
             autocomplete="off"
             hx-get="/members/keluarga/search/"
             hx-trigger="keyup changed delay:300ms"
             hx-target="#keluarga-search-results"
             hx-indicator="#keluarga-search-spinner"
             name="q">
      <span id="keluarga-search-spinner" class="htmx-indicator spinner-border spinner-border-sm text-secondary position-absolute"
            style="right:10px;top:10px" role="status"></span>
    </div>
    <div id="keluarga-search-results" class="position-relative"></div>
  </div>

  <div class="row g-3 mb-3">
    <div class="col-6">
      <label class="form-label">Bulan Periode *</label>
      {{ form.period_month }}
    </div>
    <div class="col-6">
      <label class="form-label">Tahun Periode *</label>
      {{ form.period_year }}
    </div>
  </div>
  <div class="mb-3">
    <label class="form-label">Jumlah (Rp) *</label>
    {{ form.amount }}
  </div>
  <div class="mb-3">
    <label class="form-label">Tanggal &amp; Waktu Terima *</label>
    {{ form.date_received }}
  </div>
  <div class="mb-3">
    <label class="form-label">Catatan</label>
    {{ form.notes }}
  </div>

  <button type="submit" class="btn btn-primary">Simpan</button>
  <a href="/payments/" class="btn btn-outline-secondary ms-2">Batal</a>
</form>

<script>
const PKSS_NAME = 'Iuran PKSS';

function selectMember(id, label) {
  document.getElementById('member-id-hidden').value = id;
  document.getElementById('member-search-input').value = label;
  document.getElementById('member-search-results').innerHTML = '';
}

function selectKeluarga(id, label) {
  document.getElementById('keluarga-id-hidden').value = id;
  document.getElementById('keluarga-search-input').value = label;
  document.getElementById('keluarga-search-results').innerHTML = '';
}

function togglePaymentFields() {
  const select = document.getElementById('id_payment_type');
  const selectedText = select.options[select.selectedIndex]?.text || '';
  const isPKSS = selectedText === PKSS_NAME;
  document.getElementById('member-field').style.display = isPKSS ? '' : 'none';
  document.getElementById('keluarga-field').style.display = isPKSS ? 'none' : '';
}

document.getElementById('id_payment_type').addEventListener('change', togglePaymentFields);
togglePaymentFields();

{% if prefill_member %}
document.addEventListener('DOMContentLoaded', function() {
  selectMember('{{ prefill_member.pk }}', '{{ prefill_member.full_name }} ({{ prefill_member.member_id }})');
});
{% endif %}
</script>
{% endblock %}
```

- [ ] **Step 7: Smoke test the form in the browser**

```bash
python manage.py runserver
```

- Open `/payments/new/`
- Verify: selecting "Iuran PKSS" shows member search, selecting "Iuran Kartu Kuning" shows KK search
- Verify: submitting with no member/KK shows appropriate error

- [ ] **Step 8: Commit**

```bash
git add members/views.py members/urls.py \
        members/templates/members/partials/keluarga_search_results.html \
        payments/forms.py payments/views.py \
        payments/templates/payments/new.html
git commit -m "feat: dynamic payment form -- member search for PKSS, KK search for Kartu Kuning"
```

---

## Task 4: Payment List — Two Tabs + Batch Report Action

**Files:**
- Modify: `payments/views.py` (update payment_list, add batch_report)
- Modify: `payments/urls.py`
- Modify: `payments/templates/payments/list.html`
- Modify: `payments/templates/payments/partials/payment_table.html`

**Interfaces:**
- Consumes: `Payment` with `is_reported`, `date_reported`, `date_received` from Task 2
- Produces: `batch_report` view at `POST /payments/batch-report/` that stamps `date_reported` on selected payments

- [ ] **Step 1: Add batch_report view to payments/views.py**

Add this function to `payments/views.py`:

```python
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
```

- [ ] **Step 2: Update payment_list view to support tabs**

Replace the `payment_list` function in `payments/views.py` with:

```python
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
        'months': range(1, 13),
        'years': range(now.year - 2, now.year + 2),
    }

    if request.htmx:
        return render(request, 'payments/partials/payment_table.html', context)
    return render(request, 'payments/list.html', context)
```

Also add `from django.db import models` at the top of `payments/views.py`.

- [ ] **Step 3: Add batch_report URL to payments/urls.py**

```python
from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.record_payment, name='record_payment'),
    path('', views.payment_list, name='payment_list'),
    path('batch-report/', views.batch_report, name='batch_report'),
]
```

- [ ] **Step 4: Rewrite payments/templates/payments/list.html**

```html
{% extends 'base.html' %}
{% load idr_filters %}
{% block title %}Daftar Pembayaran{% endblock %}
{% block content %}
<h3>Daftar Pembayaran</h3>

<ul class="nav nav-tabs mb-3">
  <li class="nav-item">
    <a class="nav-link {% if tab == 'belum' %}active{% endif %}"
       href="?tab=belum&month={{ month }}&year={{ year }}">Belum Dilaporkan</a>
  </li>
  <li class="nav-item">
    <a class="nav-link {% if tab == 'sudah' %}active{% endif %}"
       href="?tab=sudah&month={{ month }}&year={{ year }}">Sudah Dilaporkan</a>
  </li>
</ul>

<div class="row g-2 mb-3 align-items-center"
     hx-get="/payments/"
     hx-trigger="change from:select, change from:input[type=number]"
     hx-target="#payment-table-body"
     hx-indicator="#table-spinner"
     hx-include="[name='month'],[name='year'],[name='payment_type'],[name='wilayah'],[name='lingkungan'],[name='tab']">
  <input type="hidden" name="tab" value="{{ tab }}">
  <div class="col-auto">
    <select name="month" class="form-select">
      {% for m in months %}
      <option value="{{ m }}" {% if m == month %}selected{% endif %}>{{ m }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="col-auto">
    <select name="year" class="form-select">
      {% for y in years %}
      <option value="{{ y }}" {% if y == year %}selected{% endif %}>{{ y }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="col-auto">
    <select name="payment_type" class="form-select">
      <option value="">Semua Jenis</option>
      {% for pt in payment_types %}
      <option value="{{ pt.pk }}" {% if selected_payment_type == pt.pk|stringformat:"s" %}selected{% endif %}>{{ pt.name }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="col-auto">
    <a href="/payments/?tab={{ tab }}" class="btn btn-outline-secondary">Reset</a>
  </div>
  <div class="col-auto">
    <span id="table-spinner" class="htmx-indicator spinner-border spinner-border-sm text-secondary" role="status"></span>
  </div>
</div>

<form method="post" action="/payments/batch-report/" id="batch-form">
  {% csrf_token %}
  <div id="payment-table-body">
    {% include 'payments/partials/payment_table.html' %}
  </div>
  {% if tab == 'belum' and payments %}
  <div class="mt-3">
    <button type="submit" class="btn btn-warning"
            onclick="return confirm('Laporkan pembayaran yang dipilih ke Bendahara Utama?')">
      Laporkan ke Bendahara Utama
    </button>
  </div>
  {% endif %}
</form>
{% endblock %}
```

- [ ] **Step 5: Rewrite payments/templates/payments/partials/payment_table.html**

```html
{% load idr_filters %}
<div class="table-responsive">
  <table class="table table-striped table-hover">
    <thead class="table-dark">
      <tr>
        {% if tab == 'belum' %}<th><input type="checkbox" id="select-all"></th>{% endif %}
        <th>Anggota / KK</th><th>Lingkungan</th><th>Jenis</th>
        <th>Jumlah (Rp)</th><th>Tgl Terima</th>
        {% if tab == 'sudah' %}<th>Tgl Lapor</th>{% endif %}
      </tr>
    </thead>
    <tbody>
      {% for p in payments %}
      <tr>
        {% if tab == 'belum' %}
        <td><input type="checkbox" name="payment_ids" value="{{ p.pk }}"></td>
        {% endif %}
        <td>
          {% if p.member %}
            <a href="/members/{{ p.member.pk }}/">{{ p.member.full_name }}</a>
          {% else %}
            {{ p.keluarga }}
          {% endif %}
        </td>
        <td>
          {% if p.member %}{{ p.member.lingkungan.name }}
          {% else %}{{ p.keluarga.lingkungan.name }}{% endif %}
        </td>
        <td>{{ p.payment_type.name }}</td>
        <td>{{ p.amount|idr }}</td>
        <td>{{ p.date_received|date:"d M Y H:i" }}</td>
        {% if tab == 'sudah' %}
        <td>{{ p.date_reported|date:"d M Y H:i" }}</td>
        {% endif %}
      </tr>
      {% empty %}
      <tr>
        <td colspan="7" class="text-center text-muted">
          {% if tab == 'belum' %}Semua pembayaran sudah dilaporkan.
          {% else %}Belum ada pembayaran yang dilaporkan.{% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
    {% if payments %}
    <tfoot>
      <tr class="table-info fw-bold">
        <td colspan="{% if tab == 'belum' %}3{% else %}3{% endif %}">Total</td>
        <td>{{ payments|length }} transaksi</td>
        <td colspan="3"></td>
      </tr>
    </tfoot>
    {% endif %}
  </table>
</div>

<script>
const selectAll = document.getElementById('select-all');
if (selectAll) {
  selectAll.addEventListener('change', function() {
    document.querySelectorAll('input[name="payment_ids"]').forEach(cb => cb.checked = this.checked);
  });
}
</script>
```

- [ ] **Step 6: Verify in browser**

- Open `/payments/` — verify two tabs appear
- Switch to "Belum Dilaporkan" — verify checkboxes and "Laporkan" button appear
- Select payments and click "Laporkan" — verify success message and payments move to "Sudah Dilaporkan" tab

- [ ] **Step 7: Commit**

```bash
git add payments/views.py payments/urls.py \
        payments/templates/payments/list.html \
        payments/templates/payments/partials/payment_table.html
git commit -m "feat: payment list tabs (Belum/Sudah Dilaporkan) with batch report action"
```

---

## Task 5: Laporan Masuk — Super Admin Confirmation Page

**Files:**
- Modify: `payments/views.py` (add laporan_masuk, confirm_laporan)
- Modify: `payments/urls.py`
- Create: `payments/templates/payments/laporan_masuk.html`
- Modify: `templates/base.html` (add nav link)

**Interfaces:**
- Consumes: `Payment` with `date_reported`, `date_confirmed`, `confirmed_by` from Task 2
- Produces: `laporan_masuk` at `/payments/laporan-masuk/` (Super Admin only); `confirm_laporan` at `POST /payments/confirm/`

- [ ] **Step 1: Add laporan_masuk and confirm_laporan views to payments/views.py**

Add these imports at the top of `payments/views.py`:

```python
from django.utils import timezone
from church_payment.mixins import SuperAdminRequired
from django.views import View
```

Add these functions to `payments/views.py`:

```python
from church_payment.mixins import SuperAdminRequired
from django.views import View


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
```

- [ ] **Step 2: Add URLs to payments/urls.py**

```python
from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.record_payment, name='record_payment'),
    path('', views.payment_list, name='payment_list'),
    path('batch-report/', views.batch_report, name='batch_report'),
    path('laporan-masuk/', views.LaporanMasukView.as_view(), name='laporan_masuk'),
    path('confirm/', views.confirm_laporan, name='confirm_laporan'),
]
```

- [ ] **Step 3: Create payments/templates/payments/laporan_masuk.html**

```html
{% extends 'base.html' %}
{% load idr_filters %}
{% block title %}Laporan Masuk{% endblock %}
{% block content %}
<h3>Laporan Masuk</h3>
<p class="text-muted">Pembayaran yang telah dilaporkan oleh bendahara dan menunggu konfirmasi.</p>

{% if not batches %}
<div class="alert alert-success">Tidak ada laporan yang menunggu konfirmasi.</div>
{% endif %}

{% for batch in batches %}
<div class="card mb-4">
  <div class="card-header d-flex justify-content-between align-items-center">
    <div>
      <strong>{{ batch.treasurer.get_full_name|default:batch.treasurer.username }}</strong>
      <span class="text-muted ms-2">dilaporkan {{ batch.date_reported }}</span>
    </div>
    <span class="badge bg-secondary">{{ batch.payments|length }} transaksi — Rp {{ batch.total|idr }}</span>
  </div>
  <div class="card-body p-0">
    <form method="post" action="/payments/confirm/">
      {% csrf_token %}
      <div class="table-responsive">
        <table class="table table-sm mb-0">
          <thead class="table-light">
            <tr>
              <th><input type="checkbox" class="batch-select-all"></th>
              <th>Anggota / KK</th><th>Lingkungan</th><th>Jenis</th>
              <th>Jumlah (Rp)</th><th>Tgl Terima</th>
            </tr>
          </thead>
          <tbody>
            {% for p in batch.payments %}
            <tr>
              <td><input type="checkbox" name="payment_ids" value="{{ p.pk }}" checked></td>
              <td>
                {% if p.member %}{{ p.member.full_name }}
                {% else %}{{ p.keluarga }}{% endif %}
              </td>
              <td>
                {% if p.member %}{{ p.member.lingkungan.name }}
                {% else %}{{ p.keluarga.lingkungan.name }}{% endif %}
              </td>
              <td>{{ p.payment_type.name }}</td>
              <td>{{ p.amount|idr }}</td>
              <td>{{ p.date_received|date:"d M Y H:i" }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      <div class="card-footer">
        <button type="submit" class="btn btn-success btn-sm"
                onclick="return confirm('Konfirmasi laporan ini?')">
          &#10003; Konfirmasi
        </button>
      </div>
    </form>
  </div>
</div>
{% endfor %}

<script>
document.querySelectorAll('.batch-select-all').forEach(cb => {
  cb.addEventListener('change', function() {
    this.closest('form').querySelectorAll('input[name="payment_ids"]')
      .forEach(c => c.checked = this.checked);
  });
});
</script>
{% endblock %}
```

- [ ] **Step 4: Add Laporan Masuk link to templates/base.html**

In `templates/base.html`, find the `{% if is_super_admin %}` block inside the navbar and add the Laporan Masuk link:

```html
{% if is_super_admin %}
<li class="nav-item">
  <a class="nav-link" href="/payments/laporan-masuk/">Laporan Masuk</a>
</li>
<li class="nav-item dropdown">
```

- [ ] **Step 5: Verify in browser**

- Log in as Super Admin
- Ensure "Laporan Masuk" appears in navbar
- Open `/payments/laporan-masuk/` — verify reported batches appear
- Click "Konfirmasi" — verify success message and batch disappears

- [ ] **Step 6: Commit**

```bash
git add payments/views.py payments/urls.py \
        payments/templates/payments/laporan_masuk.html \
        templates/base.html
git commit -m "feat: Laporan Masuk page for Super Admin to confirm treasurer reports"
```

---

## Task 6: Keluarga Management in Settings Admin

**Files:**
- Modify: `settings_admin/forms.py`
- Modify: `settings_admin/views.py`
- Modify: `settings_admin/urls.py`
- Create: `settings_admin/templates/settings_admin/keluarga.html`
- Modify: `templates/base.html` (add Keluarga link in Pengaturan dropdown)

**Interfaces:**
- Consumes: `Keluarga` from `members.models` (Task 1)
- Produces: `KeluargaListView` at `/settings/keluarga/` (Super Admin only)

- [ ] **Step 1: Add KeluargaForm to settings_admin/forms.py**

Read `settings_admin/forms.py` first, then add:

```python
from members.models import Wilayah, Lingkungan, Keluarga

class KeluargaForm(forms.ModelForm):
    class Meta:
        model = Keluarga
        fields = ['kk_number', 'name', 'lingkungan', 'is_active']
        widgets = {
            'kk_number': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'lingkungan': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
```

- [ ] **Step 2: Add KeluargaListView to settings_admin/views.py**

Add this import at the top:

```python
from members.models import Wilayah, Lingkungan, Keluarga
```

Add this class:

```python
class KeluargaListView(SuperAdminRequired, View):
    def get(self, request):
        from .forms import KeluargaForm
        return render(request, 'settings_admin/keluarga.html', {
            'keluarga_list': Keluarga.objects.select_related('lingkungan__wilayah').all(),
            'form': KeluargaForm(),
        })

    def post(self, request):
        from .forms import KeluargaForm
        form = KeluargaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Keluarga berhasil ditambahkan.')
            return redirect('settings_keluarga')
        return render(request, 'settings_admin/keluarga.html', {
            'keluarga_list': Keluarga.objects.select_related('lingkungan__wilayah').all(),
            'form': form,
        })
```

- [ ] **Step 3: Add URL to settings_admin/urls.py**

```python
from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.UserListView.as_view(), name='settings_users'),
    path('wilayah/', views.WilayahListView.as_view(), name='settings_wilayah'),
    path('lingkungan/', views.WilayahListView.as_view(), name='settings_lingkungan'),
    path('payment-types/', views.PaymentTypeListView.as_view(), name='settings_payment_types'),
    path('keluarga/', views.KeluargaListView.as_view(), name='settings_keluarga'),
]
```

- [ ] **Step 4: Create settings_admin/templates/settings_admin/keluarga.html**

```html
{% extends 'base.html' %}
{% block title %}Keluarga (KK){% endblock %}
{% block content %}
<h3>Manajemen Keluarga (KK)</h3>
<div class="row">
  <div class="col-md-8">
    <div class="table-responsive">
      <table class="table table-striped">
        <thead class="table-dark">
          <tr><th>No. KK</th><th>Nama Keluarga</th><th>Lingkungan</th><th>Wilayah</th><th>Status</th></tr>
        </thead>
        <tbody>
          {% for kk in keluarga_list %}
          <tr>
            <td>{{ kk.kk_number }}</td>
            <td>{{ kk.name }}</td>
            <td>{{ kk.lingkungan.name }}</td>
            <td>{{ kk.lingkungan.wilayah.name }}</td>
            <td>
              {% if kk.is_active %}<span class="badge bg-success">Aktif</span>
              {% else %}<span class="badge bg-secondary">Nonaktif</span>{% endif %}
            </td>
          </tr>
          {% empty %}
          <tr><td colspan="5" class="text-muted text-center">Belum ada data Keluarga.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  <div class="col-md-4">
    <div class="card">
      <div class="card-header">Tambah Keluarga</div>
      <div class="card-body">
        <form method="post">
          {% csrf_token %}
          <div class="mb-2">
            <label class="form-label">Nomor KK</label>
            {{ form.kk_number }}
          </div>
          <div class="mb-2">
            <label class="form-label">Nama Keluarga</label>
            {{ form.name }}
          </div>
          <div class="mb-2">
            <label class="form-label">Lingkungan</label>
            {{ form.lingkungan }}
          </div>
          <div class="mb-2 form-check">
            {{ form.is_active }}
            <label class="form-check-label">Aktif</label>
          </div>
          <button type="submit" class="btn btn-primary w-100">Simpan</button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Add Keluarga link to base.html Pengaturan dropdown**

In `templates/base.html`, inside the Super Admin dropdown menu, add:

```html
<li><a class="dropdown-item" href="/settings/keluarga/">Keluarga (KK)</a></li>
```

- [ ] **Step 6: Verify in browser**

- Log in as Super Admin → Pengaturan → Keluarga (KK)
- Add a test KK — verify it appears in the list
- Open `/payments/new/` → select "Iuran Kartu Kuning" → type in KK search → verify the new KK appears

- [ ] **Step 7: Commit**

```bash
git add settings_admin/forms.py settings_admin/views.py settings_admin/urls.py \
        settings_admin/templates/settings_admin/keluarga.html \
        templates/base.html
git commit -m "feat: Keluarga (KK) management in settings admin"
```

---

## Task 7: Fix Reports and Member Detail for Renamed Fields

**Files:**
- Modify: `reports/views.py` (date_paid → date_received)
- Modify: `reports/exporters.py` (date_paid → date_received)
- Modify: `members/templates/members/detail.html` (handle nullable member/keluarga on payments)

**Interfaces:**
- Consumes: `Payment.date_received` from Task 2 (replaces old `date_paid`)

- [ ] **Step 1: Update reports/views.py**

Read the file, then replace every reference to `date_paid` with `date_received`. Also update the member detail view — `member.payments` now may include keluarga payments; filter to only member-linked ones:

In `members/views.py`, update `member_detail`:

```python
@login_required
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    payments = member.payments.select_related('payment_type', 'recorded_by').order_by('-period_year', '-period_month')
    return render(request, 'members/detail.html', {'member': member, 'payments': payments})
```

(No change needed here — `member.payments` already filters by member FK.)

- [ ] **Step 2: Update reports/exporters.py**

Read the file. Replace every occurrence of `date_paid` with `date_received`. Replace every occurrence of `p.date_paid` with `p.date_received`.

- [ ] **Step 3: Update members/templates/members/detail.html payment table**

The payment history table shows `p.amount|idr` — verify it still works. Update the date column header and value from `date_paid` to `date_received` if present:

In the payment table, change:
- Column header: `Tgl Bayar` → `Tgl Terima`
- Value: `{{ p.date_paid|date:"d M Y H:i" }}` → `{{ p.date_received|date:"d M Y H:i" }}`

- [ ] **Step 4: Check for any remaining date_paid references**

```bash
grep -r "date_paid" . --include="*.py" --include="*.html" --exclude-dir=venv --exclude-dir=.git
```

Expected: zero results.

- [ ] **Step 5: Run the app and verify reports load**

```bash
python manage.py runserver
```

Open `/reports/monthly/`, `/reports/annual/`, `/reports/unpaid/` — verify no errors.

- [ ] **Step 6: Commit**

```bash
git add reports/views.py reports/exporters.py \
        members/templates/members/detail.html
git commit -m "fix: rename date_paid to date_received across reports and templates"
```

---

## Task 8: Seed Data and Payment Type Cleanup

**Files:**
- Modify: `members/management/commands/seed_dummy_data.py`
- Database: manually update or migration for payment type names

**Interfaces:**
- Produces: only "Iuran PKSS" and "Iuran Kartu Kuning" payment types in the system

- [ ] **Step 1: Update seed_dummy_data.py payment types**

In `members/management/commands/seed_dummy_data.py`, find where payment types are created or referenced and replace with:

```python
pkss, _ = PaymentType.objects.get_or_create(
    name='Iuran PKSS',
    defaults={'description': 'Iuran PKSS per anggota', 'is_active': True}
)
kartu_kuning, _ = PaymentType.objects.get_or_create(
    name='Iuran Kartu Kuning',
    defaults={'description': 'Iuran Kartu Kuning per KK', 'is_active': True}
)
```

Remove any creation of tithe/persembahan types.

- [ ] **Step 2: Clean up payment types in the database**

```bash
python manage.py shell -c "
from payments.models import PaymentType
# Deactivate old types
PaymentType.objects.exclude(name__in=['Iuran PKSS','Iuran Kartu Kuning']).update(is_active=False)
# Create the two correct types if they don't exist
PaymentType.objects.get_or_create(name='Iuran PKSS', defaults={'is_active': True})
PaymentType.objects.get_or_create(name='Iuran Kartu Kuning', defaults={'is_active': True})
print('Payment types:', list(PaymentType.objects.values_list('name','is_active')))
"
```

Expected output: `[('Iuran PKSS', True), ('Iuran Kartu Kuning', True), ...]` — old types show `is_active=False`.

- [ ] **Step 3: Verify form only shows two types**

Open `/payments/new/` — the payment type dropdown should show only "Iuran PKSS" and "Iuran Kartu Kuning".

- [ ] **Step 4: Commit**

```bash
git add members/management/commands/seed_dummy_data.py
git commit -m "chore: update seed data and payment types to PKSS + Kartu Kuning only"
```

---

## Final Verification Checklist

- [ ] `/payments/new/` — selecting PKSS shows member search; selecting Kartu Kuning shows KK search
- [ ] Recording PKSS payment saves with `member` set, `keluarga` null
- [ ] Recording Kartu Kuning payment saves with `keluarga` set, `member` null
- [ ] Duplicate PKSS payment for same member+period shows error
- [ ] Duplicate Kartu Kuning payment for same KK+period shows error
- [ ] `/payments/` — "Belum Dilaporkan" tab shows unreported payments with checkboxes
- [ ] Selecting payments and clicking "Laporkan" stamps `date_reported` and moves them to "Sudah Dilaporkan"
- [ ] `/payments/laporan-masuk/` — Super Admin sees submitted batches
- [ ] Clicking "Konfirmasi" stamps `date_confirmed` and `confirmed_by`, batch disappears
- [ ] `/settings/keluarga/` — can add new KK records
- [ ] `/reports/monthly/` and `/reports/annual/` — no errors
- [ ] `/members/<pk>/` — payment history shows `Tgl Terima` column correctly
- [ ] No `date_paid` references remain in codebase
