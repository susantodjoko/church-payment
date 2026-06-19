import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from io import BytesIO


def _header_style(ws, row, headers):
    fill = PatternFill(fill_type='solid', fgColor='1F3864')
    font = Font(color='FFFFFF', bold=True)
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=h)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal='center')


def build_monthly_excel(payments, month, year):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f'Laporan {month}-{year}'
    ws.cell(1, 1, f'Laporan Pembayaran Bulan {month}/{year}').font = Font(bold=True, size=14)
    headers = ['No', 'Anggota', 'Lingkungan', 'Wilayah', 'Jenis', 'Jumlah (Rp)', 'Tgl Terima', 'Dicatat oleh']
    _header_style(ws, 3, headers)
    for i, p in enumerate(payments, 1):
        ws.append([
            i,
            p.member.full_name,
            p.member.lingkungan.name,
            p.member.lingkungan.wilayah.name,
            p.payment_type.name,
            float(p.amount),
            p.date_received.strftime('%d/%m/%Y %H:%M'),
            p.recorded_by.get_full_name() or p.recorded_by.username,
        ])
    ws.append([])
    ws.append(['', '', '', '', 'TOTAL', sum(float(p.amount) for p in payments)])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def build_annual_excel(year, monthly_totals, member_summary):
    wb = openpyxl.Workbook()

    # Sheet 1: month-by-month totals
    ws1 = wb.active
    ws1.title = 'Rekapitulasi Bulanan'
    ws1.cell(1, 1, f'Laporan Tahunan {year}').font = Font(bold=True, size=14)
    _header_style(ws1, 3, ['Bulan', 'Total Pembayaran (Rp)', 'Jumlah Transaksi'])
    for row in monthly_totals:
        ws1.append(row)

    # Sheet 2: per-member summary
    ws2 = wb.create_sheet('Per Anggota')
    _header_style(ws2, 1, ['Anggota', 'Lingkungan', 'Bulan Dibayar', 'Total (Rp)', 'Belum Bayar (bulan)'])
    for row in member_summary:
        ws2.append(row)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def build_unpaid_excel(unpaid_members, month, year, payment_type_name):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Belum Bayar'
    ws.cell(1, 1, f'Anggota Belum Bayar — {payment_type_name} {month}/{year}').font = Font(bold=True, size=14)
    _header_style(ws, 3, ['No', 'ID Anggota', 'Nama', 'Lingkungan', 'Wilayah', 'Telepon'])
    for i, m in enumerate(unpaid_members, 1):
        ws.append([
            i, m.member_id, m.full_name,
            m.lingkungan.name, m.lingkungan.wilayah.name,
            m.phone or '-',
        ])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
