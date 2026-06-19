# Payment Workflow Redesign

**Date:** 2026-06-19
**Status:** Approved

---

## Overview

Redesign the church payment system to support two specific payment types, a family-based payment unit (KK), and a two-stage reporting workflow between local treasurers and the main treasurer.

---

## Payment Types

Only two payment types exist in the system:

| Type | Paid by |
|---|---|
| **Iuran PKSS** | Individual member |
| **Iuran Kartu Kuning** | Family unit (KK / Keluarga) |

All other payment types (tithe/persembahan) are removed.

---

## Data Model Changes

### New model: `Keluarga` (in `members` app)

| Field | Type | Notes |
|---|---|---|
| `kk_number` | CharField, unique | e.g. "KK-001" |
| `name` | CharField | e.g. "Keluarga Budi Santoso" |
| `lingkungan` | FK → Lingkungan | family belongs to a lingkungan |
| `is_active` | BooleanField | default True |

### Modified model: `Payment`

| Change | Detail |
|---|---|
| Rename `date_paid` → `date_received` | when local treasurer physically received the money |
| Make `member` nullable | null for Kartu Kuning payments |
| Add `keluarga` | FK → Keluarga, nullable — required for Kartu Kuning, null for PKSS |
| Add `date_reported` | DateTimeField, nullable — set automatically when treasurer submits batch |
| Add `date_confirmed` | DateTimeField, nullable — set when main treasurer confirms |
| Add `confirmed_by` | FK → User, nullable — which Super Admin confirmed |

**Constraint:** exactly one of `member` or `keluarga` is set per payment, enforced at form level.

**Payment lifecycle:**

```
Dicatat       → date_received set, date_reported null
Dilaporkan    → date_reported set (batch action by local treasurer)
Dikonfirmasi  → date_confirmed + confirmed_by set (action by main treasurer)
```

---

## User Roles

| Role | Responsibilities |
|---|---|
| **Treasurer** (local) | Record payments, submit batch reports to main treasurer |
| **Super Admin** (main treasurer) | Confirm incoming reports, view consolidated data, manage settings |

---

## Workflow

### Local Treasurer

1. **Record payment** — choose Iuran PKSS (→ member search) or Iuran Kartu Kuning (→ KK dropdown). Fill amount + `Tanggal Terima`.
2. **Review unreported payments** — view "Belum Dilaporkan" tab on payment list.
3. **Submit batch report** — select payments via checkbox → click **"Laporkan ke Bendahara Utama"** → `date_reported` stamped on all selected payments automatically.

### Main Treasurer (Super Admin)

1. **View incoming reports** — "Laporan Masuk" page lists submitted batches grouped by treasurer + `date_reported`.
2. **Review payments** — expand each batch to see individual payment rows.
3. **Confirm** — click **"Konfirmasi"** per batch → `date_confirmed` and `confirmed_by` stamped.

---

## UI Changes

### Record Payment form
- Payment type dropdown: selecting **Iuran PKSS** shows member search; selecting **Iuran Kartu Kuning** shows KK dropdown
- `Tanggal Terima` field replaces `Tanggal Bayar`
- `date_reported` and `date_confirmed` are never shown on this form — set automatically

### Payment list (Treasurer view)
- **Tab: Belum Dilaporkan** — checkbox per row + "Laporkan ke Bendahara Utama" button
- **Tab: Sudah Dilaporkan** — shows `date_reported` column, read-only

### Laporan Masuk (Super Admin only)
- Lists submitted batches grouped by treasurer + `date_reported`
- Expandable rows to show individual payments
- **"Konfirmasi"** button per batch

### Settings Admin
- Add **Keluarga management** page — add/edit KK number, name, lingkungan
- Remove old payment types (tithe, persembahan) from database and seeder

---

## Migration Notes

- Existing `date_paid` data migrates to `date_received`
- Existing `member` FK stays; `keluarga` defaults to null for all existing records
- `date_reported` and `date_confirmed` default to null for all existing records
- Seed/fixture data updated to only create Iuran PKSS and Iuran Kartu Kuning
