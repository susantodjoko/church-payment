# Bulk Upload Anggota Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Super Admin page at `/settings/upload-anggota/` that lets admins upload a CSV to bulk-create members, with a preview step before any data is written.

**Architecture:** A pure CSV-parser utility (`settings_admin/csv_utils.py`) validates each row against live DB data and returns a list of status-annotated dicts. `UploadAnggotaView` stores parsed rows in the session on POST(preview) and bulk-creates Members on POST(confirm). A separate function view serves the downloadable CSV template.

**Tech Stack:** Django 5+, Python `csv` stdlib, Bootstrap 5.3, `request.session` for preview state, `Member.objects.bulk_create`.

## Global Constraints

- All new views protected by `SuperAdminRequired` mixin (see `church_payment/mixins.py`)
- URL names: `upload_anggota`, `download_anggota_template`
- Session key: `'upload_anggota_preview'`
- After confirm, redirect to `member_list` (`/members/`)
- CSV columns (in order): `member_id`, `full_name`, `gender`, `join_date`, `lingkungan`, `date_of_birth`, `phone`, `address`, `keluarga_kk`
- `lingkungan` matched case-insensitively against `Lingkungan.name`
- Unknown `keluarga_kk` → silently set `keluarga_id=None` (not an error)
- Duplicate `member_id` → status `'conflict'` (not imported, not an error)
- Bootstrap row colour classes: `table-success` (valid), `table-warning` (conflict), `table-danger` (error)

---

### Task 1: URL wiring and template download view

**Files:**
- Modify: `settings_admin/urls.py`
- Modify: `settings_admin/views.py`
- Modify: `templates/base.html`
- Test: `tests/test_upload_anggota.py` (create new file)

**Interfaces:**
- Produces: `download_anggota_template(request)` function view, URLs `upload_anggota` and `download_anggota_template`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_upload_anggota.py`:

```python
import io
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User, Group
from members.models import Wilayah, Lingkungan, Member


def make_super_admin():
    Group.objects.get_or_create(name='Super Admin')
    Group.objects.get_or_create(name='Treasurer')
    u = User.objects.create_user('admin', password='pass')
    u.groups.add(Group.objects.get(name='Super Admin'))
    return u


def make_treasurer():
    Group.objects.get_or_create(name='Treasurer')
    u = User.objects.create_user('treasurer', password='pass')
    u.groups.add(Group.objects.get(name='Treasurer'))
    return u


class TemplateDownloadTest(TestCase):
    def setUp(self):
        self.admin = make_super_admin()
        self.client.login(username='admin', password='pass')

    def test_template_download_returns_csv(self):
        response = self.client.get('/settings/upload-anggota/template/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment', response['Content-Disposition'])
        content = response.content.decode('utf-8')
        self.assertIn('member_id', content)
        self.assertIn('full_name', content)
        self.assertIn('gender', content)
        self.assertIn('join_date', content)
        self.assertIn('lingkungan', content)

    def test_template_download_has_example_rows(self):
        response = self.client.get('/settings/upload-anggota/template/')
        lines = response.content.decode('utf-8').strip().splitlines()
        self.assertGreaterEqual(len(lines), 3)  # header + 2 example rows

    def test_treasurer_cannot_download_template(self):
        t = make_treasurer()
        self.client.login(username='treasurer', password='pass')
        response = self.client.get('/settings/upload-anggota/template/')
        self.assertEqual(response.status_code, 403)

    def test_upload_page_get_returns_200(self):
        response = self.client.get('/settings/upload-anggota/')
        self.assertEqual(response.status_code, 200)

    def test_treasurer_cannot_access_upload_page(self):
        t = make_treasurer()
        self.client.login(username='treasurer', password='pass')
        response = self.client.get('/settings/upload-anggota/')
        self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

```
python manage.py test tests.test_upload_anggota.TemplateDownloadTest -v 2
```

Expected: FAIL — URLs don't exist yet (404 or ImportError).

- [ ] **Step 3: Add URLs**

In `settings_admin/urls.py`, add two paths:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.UserListView.as_view(), name='settings_users'),
    path('wilayah/', views.WilayahListView.as_view(), name='settings_wilayah'),
    path('lingkungan/', views.WilayahListView.as_view(), name='settings_lingkungan'),
    path('payment-types/', views.PaymentTypeListView.as_view(), name='settings_payment_types'),
    path('keluarga/', views.KeluargaListView.as_view(), name='settings_keluarga'),
    path('keluarga/<int:pk>/toggle-active/', views.KeluargaToggleActiveView.as_view(), name='keluarga_toggle_active'),
    path('upload-anggota/', views.UploadAnggotaView.as_view(), name='upload_anggota'),
    path('upload-anggota/template/', views.download_anggota_template, name='download_anggota_template'),
]
```

- [ ] **Step 4: Add stub view and template download to `settings_admin/views.py`**

Add at the bottom of `settings_admin/views.py`:

```python
import csv
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied


def download_anggota_template(request):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
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
        # stubs — implemented in later tasks
        return render(request, 'settings_admin/upload_anggota.html')
```

- [ ] **Step 5: Create stub template**

Create `settings_admin/templates/settings_admin/upload_anggota.html`:

```html
{% extends 'base.html' %}
{% block title %}Upload Anggota{% endblock %}
{% block content %}
<h3>Upload Anggota Massal</h3>
<p>Stub — akan diimplementasikan.</p>
{% endblock %}
```

- [ ] **Step 6: Add nav link to Pengaturan dropdown in `templates/base.html`**

Inside the `{% if is_super_admin %}` dropdown block, after the existing Keluarga link, add:

```html
<li><a class="dropdown-item" href="{% url 'upload_anggota' %}">Upload Anggota</a></li>
```

The dropdown block currently ends with:
```html
<li><a class="dropdown-item" href="/settings/keluarga/">Keluarga (KK)</a></li>
```
Add the new line immediately after it, before `</ul>`.

- [ ] **Step 7: Run tests to verify they pass**

```
python manage.py test tests.test_upload_anggota.TemplateDownloadTest -v 2
```

Expected: All 5 pass.

- [ ] **Step 8: Commit**

```bash
git add settings_admin/urls.py settings_admin/views.py settings_admin/templates/settings_admin/upload_anggota.html templates/base.html tests/test_upload_anggota.py
git commit -m "feat: add upload anggota URL routing, template download, stub view"
```

---

### Task 2: CSV parser utility

**Files:**
- Create: `settings_admin/csv_utils.py`
- Test: `tests/test_upload_anggota.py` (add `ParseAnggotaCsvTest` class)

**Interfaces:**
- Produces: `parse_anggota_csv(file_obj) -> list[dict]`
  - `file_obj`: any file-like object with a `.read()` method returning bytes
  - Returns list of dicts, each with keys: `row` (int), `status` (`'valid'`|`'conflict'`|`'error'`), `member_id`, `full_name`, `gender`, `join_date` (str `YYYY-MM-DD` or original input on error), `lingkungan` (original name), `lingkungan_id` (int or None), `date_of_birth` (str `YYYY-MM-DD` or None), `phone` (str or None), `address` (str or None), `keluarga_id` (int or None), `error` (str or None)
  - Raises `ValueError` if the file cannot be decoded as UTF-8

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_upload_anggota.py`:

```python
import io
from settings_admin.csv_utils import parse_anggota_csv


class ParseAnggotaCsvTest(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Super Admin')
        Group.objects.get_or_create(name='Treasurer')
        self.w = Wilayah.objects.create(name='W1')
        self.l = Lingkungan.objects.create(name='St. Maria', wilayah=self.w)

    def _csv(self, data_rows):
        header = 'member_id,full_name,gender,join_date,lingkungan,date_of_birth,phone,address,keluarga_kk'
        content = '\n'.join([header] + data_rows)
        return io.BytesIO(content.encode('utf-8'))

    def test_valid_row_returns_valid_status(self):
        f = self._csv(['BML001,Budi Santoso,M,2024-01-15,St. Maria,,08123,,'])
        rows = parse_anggota_csv(f)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'valid')
        self.assertEqual(rows[0]['member_id'], 'BML001')
        self.assertEqual(rows[0]['lingkungan_id'], self.l.pk)
        self.assertEqual(rows[0]['row'], 2)

    def test_missing_member_id_is_error(self):
        f = self._csv([',Budi,M,2024-01-15,St. Maria,,,,'])
        rows = parse_anggota_csv(f)
        self.assertEqual(rows[0]['status'], 'error')
        self.assertIn('member_id', rows[0]['error'])

    def test_missing_full_name_is_error(self):
        f = self._csv(['BML001,,M,2024-01-15,St. Maria,,,,'])
        rows = parse_anggota_csv(f)
        self.assertEqual(rows[0]['status'], 'error')
        self.assertIn('full_name', rows[0]['error'])

    def test_invalid_gender_is_error(self):
        f = self._csv(['BML001,Budi,X,2024-01-15,St. Maria,,,,'])
        rows = parse_anggota_csv(f)
        self.assertEqual(rows[0]['status'], 'error')
        self.assertIn('gender', rows[0]['error'])

    def test_invalid_join_date_format_is_error(self):
        f = self._csv(['BML001,Budi,M,15-01-2024,St. Maria,,,,'])
        rows = parse_anggota_csv(f)
        self.assertEqual(rows[0]['status'], 'error')
        self.assertIn('join_date', rows[0]['error'])

    def test_unknown_lingkungan_is_error(self):
        f = self._csv(['BML001,Budi,M,2024-01-15,Unknown Lingkungan,,,,'])
        rows = parse_anggota_csv(f)
        self.assertEqual(rows[0]['status'], 'error')
        self.assertIn('Lingkungan', rows[0]['error'])

    def test_duplicate_member_id_is_conflict(self):
        Member.objects.create(member_id='BML001', full_name='Existing',
                               gender='M', join_date=date.today(), lingkungan=self.l)
        f = self._csv(['BML001,Budi,M,2024-01-15,St. Maria,,,,'])
        rows = parse_anggota_csv(f)
        self.assertEqual(rows[0]['status'], 'conflict')
        self.assertIn('BML001', rows[0]['error'])

    def test_lingkungan_matched_case_insensitively(self):
        f = self._csv(['BML001,Budi,M,2024-01-15,st. maria,,,,'])
        rows = parse_anggota_csv(f)
        self.assertEqual(rows[0]['status'], 'valid')
        self.assertEqual(rows[0]['lingkungan_id'], self.l.pk)

    def test_unknown_keluarga_kk_ignored(self):
        f = self._csv(['BML001,Budi,M,2024-01-15,St. Maria,,,,KK_NOT_EXIST'])
        rows = parse_anggota_csv(f)
        self.assertEqual(rows[0]['status'], 'valid')
        self.assertIsNone(rows[0]['keluarga_id'])

    def test_invalid_date_of_birth_is_error(self):
        f = self._csv(['BML001,Budi,M,2024-01-15,St. Maria,not-a-date,,,'])
        rows = parse_anggota_csv(f)
        self.assertEqual(rows[0]['status'], 'error')
        self.assertIn('date_of_birth', rows[0]['error'])

    def test_multiple_rows(self):
        f = self._csv([
            'BML001,Budi,M,2024-01-15,St. Maria,,,,',
            'BML002,Sari,F,2024-02-20,St. Maria,,,,',
        ])
        rows = parse_anggota_csv(f)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['row'], 2)
        self.assertEqual(rows[1]['row'], 3)

    def test_optional_fields_can_be_empty(self):
        f = self._csv(['BML001,Budi,M,2024-01-15,St. Maria,,,,'])
        rows = parse_anggota_csv(f)
        self.assertEqual(rows[0]['status'], 'valid')
        self.assertIsNone(rows[0]['date_of_birth'])
        self.assertIsNone(rows[0]['phone'])
        self.assertIsNone(rows[0]['address'])
        self.assertIsNone(rows[0]['keluarga_id'])
```

- [ ] **Step 2: Run tests to verify they fail**

```
python manage.py test tests.test_upload_anggota.ParseAnggotaCsvTest -v 2
```

Expected: FAIL — `settings_admin.csv_utils` does not exist.

- [ ] **Step 3: Implement `settings_admin/csv_utils.py`**

```python
import csv
import io
from datetime import datetime

from members.models import Lingkungan, Keluarga, Member


def parse_anggota_csv(file_obj):
    """
    Parse a bytes file-like object as a member CSV.
    Returns a list of row dicts with keys: row, status, member_id, full_name,
    gender, join_date, lingkungan, lingkungan_id, date_of_birth, phone,
    address, keluarga_id, error.
    Raises ValueError if the file cannot be decoded.
    """
    try:
        text = file_obj.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError('File harus dalam format UTF-8.')

    lingkungan_map = {l.name.lower(): l for l in Lingkungan.objects.all()}
    existing_ids = set(Member.objects.values_list('member_id', flat=True))
    keluarga_map = {k.kk_number: k.pk for k in Keluarga.objects.all()}

    rows = []
    reader = csv.DictReader(io.StringIO(text))
    for i, raw in enumerate(reader, start=2):
        rows.append(_validate_row(raw, i, lingkungan_map, existing_ids, keluarga_map))
    return rows


def _validate_row(raw, row_num, lingkungan_map, existing_ids, keluarga_map):
    member_id = raw.get('member_id', '').strip()
    full_name = raw.get('full_name', '').strip()
    gender = raw.get('gender', '').strip().upper()
    join_date_str = raw.get('join_date', '').strip()
    lingkungan_name = raw.get('lingkungan', '').strip()
    date_of_birth_str = raw.get('date_of_birth', '').strip()
    phone = raw.get('phone', '').strip() or None
    address = raw.get('address', '').strip() or None
    keluarga_kk = raw.get('keluarga_kk', '').strip()

    errors = []

    if not member_id:
        errors.append('member_id wajib diisi')
    if not full_name:
        errors.append('full_name wajib diisi')
    if not gender:
        errors.append('gender wajib diisi')
    elif gender not in ('M', 'F'):
        errors.append('gender harus M atau F')

    join_date = None
    if not join_date_str:
        errors.append('join_date wajib diisi')
    else:
        try:
            join_date = datetime.strptime(join_date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append('join_date format harus YYYY-MM-DD')

    lingkungan_id = None
    if not lingkungan_name:
        errors.append('lingkungan wajib diisi')
    else:
        ling = lingkungan_map.get(lingkungan_name.lower())
        if ling is None:
            errors.append(f'Lingkungan "{lingkungan_name}" tidak ditemukan')
        else:
            lingkungan_id = ling.pk

    date_of_birth = None
    if date_of_birth_str:
        try:
            date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date().isoformat()
        except ValueError:
            errors.append('date_of_birth format harus YYYY-MM-DD')

    keluarga_id = keluarga_map.get(keluarga_kk) if keluarga_kk else None

    base = {
        'row': row_num,
        'member_id': member_id,
        'full_name': full_name,
        'gender': gender,
        'join_date': join_date.isoformat() if join_date else join_date_str,
        'lingkungan': lingkungan_name,
        'lingkungan_id': lingkungan_id,
        'date_of_birth': date_of_birth,
        'phone': phone,
        'address': address,
        'keluarga_id': keluarga_id,
    }

    if errors:
        return {**base, 'status': 'error', 'error': '; '.join(errors)}

    if member_id in existing_ids:
        return {**base, 'status': 'conflict',
                'error': f'member_id "{member_id}" sudah ada di database'}

    return {**base, 'status': 'valid', 'error': None}
```

- [ ] **Step 4: Run tests to verify they pass**

```
python manage.py test tests.test_upload_anggota.ParseAnggotaCsvTest -v 2
```

Expected: All 12 pass.

- [ ] **Step 5: Commit**

```bash
git add settings_admin/csv_utils.py tests/test_upload_anggota.py
git commit -m "feat: add CSV parser utility for bulk anggota upload"
```

---

### Task 3: Upload page — GET + preview POST + template

**Files:**
- Modify: `settings_admin/views.py` (implement `UploadAnggotaView._preview`)
- Modify: `settings_admin/templates/settings_admin/upload_anggota.html` (full template)
- Test: `tests/test_upload_anggota.py` (add `UploadPreviewTest` class)

**Interfaces:**
- Consumes: `parse_anggota_csv` from `settings_admin.csv_utils`
- Produces: `UploadAnggotaView` GET and `action=preview` POST; session key `'upload_anggota_preview'`; template context keys `rows`, `valid_count`, `conflict_count`, `error_count`, `has_valid`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_upload_anggota.py`:

```python
class UploadPreviewTest(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Super Admin')
        Group.objects.get_or_create(name='Treasurer')
        self.admin = make_super_admin()
        self.client.login(username='admin', password='pass')
        self.w = Wilayah.objects.create(name='W1')
        self.l = Lingkungan.objects.create(name='St. Maria', wilayah=self.w)

    def _upload(self, rows_str):
        header = 'member_id,full_name,gender,join_date,lingkungan,date_of_birth,phone,address,keluarga_kk'
        content = (header + '\n' + rows_str).encode('utf-8')
        f = io.BytesIO(content)
        f.name = 'upload.csv'
        return self.client.post('/settings/upload-anggota/',
                                {'action': 'preview', 'csv_file': f})

    def test_get_returns_200_with_no_context_rows(self):
        response = self.client.get('/settings/upload-anggota/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('rows', response.context)

    def test_preview_valid_csv_shows_rows_in_context(self):
        response = self._upload('BML001,Budi,M,2024-01-15,St. Maria,,,,')
        self.assertEqual(response.status_code, 200)
        self.assertIn('rows', response.context)
        self.assertEqual(response.context['valid_count'], 1)
        self.assertEqual(response.context['conflict_count'], 0)
        self.assertEqual(response.context['error_count'], 0)
        self.assertTrue(response.context['has_valid'])

    def test_preview_stores_rows_in_session(self):
        self._upload('BML001,Budi,M,2024-01-15,St. Maria,,,,')
        self.assertIn('upload_anggota_preview', self.client.session)

    def test_preview_no_file_shows_error_no_rows(self):
        response = self.client.post('/settings/upload-anggota/', {'action': 'preview'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('rows', response.context)

    def test_preview_non_csv_file_shows_error(self):
        f = io.BytesIO(b'not a csv')
        f.name = 'data.txt'
        response = self.client.post('/settings/upload-anggota/',
                                    {'action': 'preview', 'csv_file': f})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('rows', response.context)

    def test_preview_shows_conflict_count(self):
        Member.objects.create(member_id='BML001', full_name='X', gender='M',
                               join_date=date.today(), lingkungan=self.l)
        response = self._upload('BML001,Budi,M,2024-01-15,St. Maria,,,,')
        self.assertEqual(response.context['conflict_count'], 1)
        self.assertEqual(response.context['valid_count'], 0)
        self.assertFalse(response.context['has_valid'])

    def test_preview_shows_error_count(self):
        response = self._upload(',Budi,M,2024-01-15,St. Maria,,,,')
        self.assertEqual(response.context['error_count'], 1)
```

- [ ] **Step 2: Run tests to verify they fail**

```
python manage.py test tests.test_upload_anggota.UploadPreviewTest -v 2
```

Expected: FAIL — view returns stub response, no context keys.

- [ ] **Step 3: Implement `_preview` in `UploadAnggotaView`**

Replace the stub `post` method in `settings_admin/views.py`:

```python
from settings_admin.csv_utils import parse_anggota_csv

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
```

- [ ] **Step 4: Build the full template**

Replace `settings_admin/templates/settings_admin/upload_anggota.html` with:

```html
{% extends 'base.html' %}
{% block title %}Upload Anggota{% endblock %}
{% block content %}
<h3>Upload Anggota Massal</h3>

{% if rows %}
  <div class="alert {% if has_valid %}alert-info{% else %}alert-warning{% endif %} mb-3">
    <strong>{{ valid_count }}</strong> valid &middot;
    <strong>{{ conflict_count }}</strong> konflik &middot;
    <strong>{{ error_count }}</strong> error
    {% if not has_valid %}
    &mdash; <em>Tidak ada baris yang dapat diimport.</em>
    {% endif %}
  </div>

  <div class="table-responsive mb-3">
    <table class="table table-sm table-bordered">
      <thead class="table-dark">
        <tr>
          <th>Baris</th><th>Status</th><th>ID Anggota</th><th>Nama</th>
          <th>Gender</th><th>Tgl Gabung</th><th>Lingkungan</th><th>Keterangan</th>
        </tr>
      </thead>
      <tbody>
        {% for r in rows %}
        <tr class="{% if r.status == 'valid' %}table-success{% elif r.status == 'conflict' %}table-warning{% else %}table-danger{% endif %}">
          <td>{{ r.row }}</td>
          <td>
            {% if r.status == 'valid' %}&#9989; Valid
            {% elif r.status == 'conflict' %}&#9888;&#65039; Konflik
            {% else %}&#10060; Error{% endif %}
          </td>
          <td>{{ r.member_id|default:"-" }}</td>
          <td>{{ r.full_name|default:"-" }}</td>
          <td>{{ r.gender|default:"-" }}</td>
          <td>{{ r.join_date|default:"-" }}</td>
          <td>{{ r.lingkungan|default:"-" }}</td>
          <td>{{ r.error|default:"-" }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <form method="post">
    {% csrf_token %}
    <input type="hidden" name="action" value="confirm">
    <button type="submit" class="btn btn-primary" {% if not has_valid %}disabled{% endif %}>
      Konfirmasi Import ({{ valid_count }} anggota)
    </button>
    <a href="{% url 'upload_anggota' %}" class="btn btn-outline-secondary ms-2">Upload File Lain</a>
  </form>

{% else %}
  <p class="text-muted mb-3">
    Upload file CSV berisi data anggota.
    <a href="{% url 'download_anggota_template' %}">Download template CSV</a>
    untuk melihat format yang benar.
  </p>

  <form method="post" enctype="multipart/form-data" style="max-width:520px">
    {% csrf_token %}
    <input type="hidden" name="action" value="preview">
    <div class="mb-3">
      <label class="form-label fw-semibold">File CSV *</label>
      <input type="file" name="csv_file" accept=".csv" class="form-control" required>
      <div class="form-text">Hanya file .csv yang diterima. Maksimal ukuran: 5 MB.</div>
    </div>
    <button type="submit" class="btn btn-primary">Preview</button>
  </form>
{% endif %}
{% endblock %}
```

- [ ] **Step 5: Run tests to verify they pass**

```
python manage.py test tests.test_upload_anggota.UploadPreviewTest -v 2
```

Expected: All 7 pass.

- [ ] **Step 6: Commit**

```bash
git add settings_admin/views.py settings_admin/templates/settings_admin/upload_anggota.html tests/test_upload_anggota.py
git commit -m "feat: implement upload preview page and template"
```

---

### Task 4: Confirm import

**Files:**
- Modify: `settings_admin/views.py` (implement `UploadAnggotaView._confirm`)
- Test: `tests/test_upload_anggota.py` (add `UploadConfirmTest` class)

**Interfaces:**
- Consumes: session key `'upload_anggota_preview'` (list of row dicts from Task 2)
- Produces: `Member` objects via `bulk_create`, redirect to `member_list`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_upload_anggota.py`:

```python
class UploadConfirmTest(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Super Admin')
        Group.objects.get_or_create(name='Treasurer')
        self.admin = make_super_admin()
        self.client.login(username='admin', password='pass')
        self.w = Wilayah.objects.create(name='W1')
        self.l = Lingkungan.objects.create(name='St. Maria', wilayah=self.w)

    def _do_preview(self, rows_str):
        header = 'member_id,full_name,gender,join_date,lingkungan,date_of_birth,phone,address,keluarga_kk'
        content = (header + '\n' + rows_str).encode('utf-8')
        f = io.BytesIO(content)
        f.name = 'upload.csv'
        self.client.post('/settings/upload-anggota/',
                         {'action': 'preview', 'csv_file': f})

    def test_confirm_creates_members_and_redirects(self):
        self._do_preview('BML001,Budi Santoso,M,2024-01-15,St. Maria,,,,')
        response = self.client.post('/settings/upload-anggota/', {'action': 'confirm'})
        self.assertRedirects(response, '/members/')
        self.assertTrue(Member.objects.filter(member_id='BML001').exists())
        m = Member.objects.get(member_id='BML001')
        self.assertEqual(m.full_name, 'Budi Santoso')
        self.assertEqual(m.lingkungan, self.l)

    def test_confirm_clears_session(self):
        self._do_preview('BML001,Budi,M,2024-01-15,St. Maria,,,,')
        self.client.post('/settings/upload-anggota/', {'action': 'confirm'})
        self.assertNotIn('upload_anggota_preview', self.client.session)

    def test_confirm_shows_success_message(self):
        self._do_preview('BML001,Budi,M,2024-01-15,St. Maria,,,,')
        response = self.client.post('/settings/upload-anggota/',
                                    {'action': 'confirm'}, follow=True)
        self.assertContains(response, '1 anggota berhasil diimport')

    def test_confirm_skips_conflict_rows(self):
        Member.objects.create(member_id='BML001', full_name='Existing',
                               gender='M', join_date=date.today(), lingkungan=self.l)
        self._do_preview(
            'BML001,Budi,M,2024-01-15,St. Maria,,,,\n'
            'BML002,Sari,F,2024-02-20,St. Maria,,,,'
        )
        self.client.post('/settings/upload-anggota/', {'action': 'confirm'})
        self.assertFalse(Member.objects.filter(member_id='BML001',
                                               full_name='Budi').exists())
        self.assertTrue(Member.objects.filter(member_id='BML002').exists())

    def test_confirm_without_session_redirects_to_upload(self):
        response = self.client.post('/settings/upload-anggota/', {'action': 'confirm'})
        self.assertRedirects(response, '/settings/upload-anggota/')
```

- [ ] **Step 2: Run tests to verify they fail**

```
python manage.py test tests.test_upload_anggota.UploadConfirmTest -v 2
```

Expected: FAIL — `_confirm` returns stub response.

- [ ] **Step 3: Implement `_confirm` in `UploadAnggotaView`**

Replace the stub `_confirm` method in `settings_admin/views.py`:

```python
from members.models import Member, Lingkungan, Keluarga

def _confirm(self, request):
    rows = request.session.get(self.SESSION_KEY)
    if not rows:
        messages.warning(request, 'Sesi telah berakhir. Silakan upload ulang.')
        return redirect('upload_anggota')

    valid_rows = [r for r in rows if r['status'] == 'valid']

    Member.objects.bulk_create([
        Member(
            member_id=r['member_id'],
            full_name=r['full_name'],
            gender=r['gender'],
            join_date=r['join_date'],
            lingkungan_id=r['lingkungan_id'],
            keluarga_id=r['keluarga_id'],
            date_of_birth=r['date_of_birth'],
            phone=r['phone'],
            address=r['address'],
        )
        for r in valid_rows
    ])

    del request.session[self.SESSION_KEY]
    messages.success(request, f'{len(valid_rows)} anggota berhasil diimport.')
    return redirect('member_list')
```

Also ensure `redirect` is imported at the top of `settings_admin/views.py` (it already is via `from django.shortcuts import render, redirect, get_object_or_404`).

Also add `Member` to the imports at the top of `settings_admin/views.py`:

```python
from members.models import Wilayah, Lingkungan, Keluarga, Member
```

- [ ] **Step 4: Run tests to verify they pass**

```
python manage.py test tests.test_upload_anggota.UploadConfirmTest -v 2
```

Expected: All 5 pass.

- [ ] **Step 5: Run the full test suite to check for regressions**

```
python manage.py test -v 1
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add settings_admin/views.py tests/test_upload_anggota.py
git commit -m "feat: implement confirm import for bulk anggota upload"
```

---

### Task 5: Run full test suite and final check

**Files:** None new — verification only.

- [ ] **Step 1: Run all tests**

```
python manage.py test -v 2
```

Expected: All tests pass, no failures.

- [ ] **Step 2: Manual smoke test**

1. Start the dev server: `python manage.py runserver`
2. Log in as `admin` / `admin123`
3. Open **Pengaturan** dropdown — confirm "Upload Anggota" appears
4. Go to `/settings/upload-anggota/`
5. Click "Download template CSV" — confirm file downloads with correct headers and 2 example rows
6. Fill in the CSV with a mix of valid, conflict (existing `member_id`), and error (bad gender) rows
7. Upload and click Preview — confirm colour-coded table and correct summary counts
8. Click "Konfirmasi Import" — confirm redirect to `/members/` with success message and new members visible

- [ ] **Step 3: Commit if any fixups were needed**

```bash
git add -A
git commit -m "fix: bulk upload anggota smoke test fixups"
```
