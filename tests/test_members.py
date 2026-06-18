from django.test import TestCase
from django.contrib.auth.models import User, Group
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


class MemberListViewTest(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Super Admin')
        Group.objects.get_or_create(name='Treasurer')
        self.user = User.objects.create_user('u', password='pass')
        self.client.login(username='u', password='pass')
        w = Wilayah.objects.create(name='W1')
        l = Lingkungan.objects.create(name='L1', wilayah=w)
        Member.objects.create(member_id='001', full_name='Alpha', gender='M',
                               join_date=date.today(), lingkungan=l)

    def test_list_returns_200(self):
        response = self.client.get('/members/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alpha')

    def test_search_partial_returns_results(self):
        response = self.client.get('/members/search/?q=alp',
                                   HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alpha')

    def test_treasurer_cannot_access_add_member(self):
        tg = Group.objects.get(name='Treasurer')
        u2 = User.objects.create_user('t1', password='pass')
        u2.groups.add(tg)
        self.client.login(username='t1', password='pass')
        response = self.client.get('/members/new/')
        self.assertEqual(response.status_code, 403)
