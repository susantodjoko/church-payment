# Bulk Upload Anggota — Design Spec

**Date:** 2026-06-23
**Feature:** Super Admin bulk member (anggota) upload via CSV
**Status:** Approved

---

## Overview

Super Admins can upload a CSV file to create multiple members (anggota) at once. The flow has two steps: upload → preview → confirm. Nothing is written to the database until the Super Admin confirms after reviewing the preview.

---

## CSV Template

Downloadable from the upload page. Contains a header row and 2 example rows.

| Column | Required | Format / Notes |
|---|---|---|
| `member_id` | ✅ | e.g. `BML001` — must be unique |
| `full_name` | ✅ | Free text |
| `gender` | ✅ | `M` or `F` |
| `join_date` | ✅ | `YYYY-MM-DD` |
| `lingkungan` | ✅ | Must exactly match an existing Lingkungan name |
| `date_of_birth` | optional | `YYYY-MM-DD` |
| `phone` | optional | Free text |
| `address` | optional | Free text |
| `keluarga_kk` | optional | KK number — matched against existing Keluarga records |

---

## Page Flow

### Step 1 — Upload (`GET /settings/upload-anggota/`)

- Download template button → `GET /settings/upload-anggota/template/`
- File picker accepting `.csv` only
- "Preview" submit button

### Step 2 — Preview (same URL, POST)

Rendered after CSV is parsed. No DB writes at this step.

- **Summary banner:** e.g. "23 valid · 2 conflicts · 1 error"
- **Preview table** with one row per CSV row, colour-coded:
  - 🟢 **Valid** — will be imported on confirm
  - 🟡 **Conflict** — `member_id` already exists in DB; will be skipped
  - 🔴 **Error** — validation failed; will be skipped
- **"Confirm Import"** button — writes valid rows to DB, redirects to `/members/` with a success flash message
- **"Upload another file"** link — returns to Step 1

### Template Download (`GET /settings/upload-anggota/template/`)

Returns a CSV file response (`Content-Disposition: attachment`) with the header row and 2 illustrative example rows.

---

## Validation Rules (per CSV row)

| Rule | Failure type |
|---|---|
| `member_id` present | ❌ Error |
| `full_name` present | ❌ Error |
| `gender` is `M` or `F` | ❌ Error |
| `join_date` is a valid `YYYY-MM-DD` date | ❌ Error |
| `lingkungan` matches an existing Lingkungan name (case-insensitive) | ❌ Error |
| `member_id` not already in DB | 🟡 Conflict |
| `date_of_birth` is a valid `YYYY-MM-DD` date (if provided) | ❌ Error |
| `keluarga_kk` matches an existing Keluarga KK number (if provided); if not found, field is ignored | — (no error) |

---

## Technical Architecture

### New files

| File | Purpose |
|---|---|
| `settings_admin/templates/settings_admin/upload_anggota.html` | Upload + preview template |

### Modified files

| File | Change |
|---|---|
| `settings_admin/views.py` | Add `UploadAnggotaView` and `download_anggota_template` |
| `settings_admin/urls.py` | Add two new URL patterns |
| `templates/base.html` | Add "Upload Anggota" to Pengaturan dropdown (Super Admin only) |

### Views

**`UploadAnggotaView`** — `SuperAdminRequired`
- `GET`: render upload form
- `POST` with `action=preview`: parse CSV in-memory, validate each row, store parsed + validated rows in `request.session`, render preview table
- `POST` with `action=confirm`: read validated rows from session, bulk-create valid Member objects, clear session key, redirect to `/members/` with success message

**`download_anggota_template`** — `SuperAdminRequired`
- Returns a CSV response with headers + 2 example rows

### Session storage (preview step)

Parsed rows stored under `request.session['upload_anggota_preview']` as a list of dicts:
```json
[
  {
    "row": 2,
    "status": "valid",
    "member_id": "BML001",
    "full_name": "Budi Santoso",
    "gender": "M",
    "join_date": "2024-01-15",
    "lingkungan_id": 3,
    "keluarga_id": 7,
    "date_of_birth": null,
    "phone": "08123456789",
    "address": null,
    "error": null
  }
]
```
`status` is one of `"valid"`, `"conflict"`, `"error"`.

---

## Navigation

"Upload Anggota" link added to the Pengaturan dropdown in `base.html`, inside the `{% if is_super_admin %}` block.

---

## Error Handling

- If no file is uploaded: show inline validation error on Step 1
- If uploaded file is not a valid CSV: show error banner on Step 1, do not proceed to preview
- If all rows are conflicts or errors (0 valid rows): show preview with disabled Confirm button and a warning "No valid rows to import"
- Session expires / confirm submitted without a valid session: redirect back to Step 1 with a warning message
