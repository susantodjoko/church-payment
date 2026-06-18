from django.test import TestCase
from members.models import Wilayah, Lingkungan, Member
from datetime import date


class WilayahModelTest(TestCase):
    def test_str(self):
        w = Wilayah.objects.create(name='Wilayah I')
        self.assertEqual(str(w), 'Wilayah I')


class LingkunganModelTest(TestCase):
    def test_str_and_wilayah_link(self):
        w = Wilayah.objects.create(name='Wilayah I')
        l = Lingkungan.objects.create(name='St. Maria', wilayah=w)
        self.assertEqual(str(l), 'St. Maria (Wilayah I)')
        self.assertEqual(l.wilayah, w)


class MemberModelTest(TestCase):
    def setUp(self):
        self.w = Wilayah.objects.create(name='Wilayah I')
        self.l = Lingkungan.objects.create(name='St. Maria', wilayah=self.w)

    def test_str(self):
        m = Member.objects.create(
            member_id='GJI-001',
            full_name='Budi Santoso',
            gender='M',
            join_date=date.today(),
            lingkungan=self.l,
        )
        self.assertEqual(str(m), 'Budi Santoso (GJI-001)')

    def test_default_is_active(self):
        m = Member.objects.create(
            member_id='GJI-002',
            full_name='Sari',
            gender='F',
            join_date=date.today(),
            lingkungan=self.l,
        )
        self.assertTrue(m.is_active)
