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
