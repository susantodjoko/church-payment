import io
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User, Group
from members.models import Wilayah, Lingkungan, Member
from settings_admin.csv_utils import parse_anggota_csv


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
