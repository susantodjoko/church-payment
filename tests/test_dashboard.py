from django.test import TestCase
from django.contrib.auth.models import User, Group
from members.models import Wilayah, Lingkungan, Member
from payments.models import PaymentType, Payment
from datetime import date
from django.utils import timezone


class DashboardTest(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Super Admin')
        Group.objects.get_or_create(name='Treasurer')
        self.user = User.objects.create_user('u', password='pass')
        self.client.login(username='u', password='pass')
        w = Wilayah.objects.create(name='W1')
        l = Lingkungan.objects.create(name='L1', wilayah=w)
        self.member = Member.objects.create(
            member_id='001', full_name='Budi', gender='M',
            join_date=date.today(), lingkungan=l)
        self.pt, _ = PaymentType.objects.get_or_create(
            name='Iuran PKSS', defaults={'is_active': True})
        now = timezone.now()
        Payment.objects.create(
            member=self.member, payment_type=self.pt, amount=75000,
            date_received=now, period_month=now.month, period_year=now.year,
            recorded_by=self.user)

    def test_dashboard_shows_this_month_total(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '75')  # part of 75000

    def test_dashboard_shows_member_count(self):
        response = self.client.get('/')
        self.assertContains(response, '1')  # 1 member
