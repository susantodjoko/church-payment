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
