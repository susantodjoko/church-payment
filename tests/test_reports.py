from django.test import TestCase
from django.contrib.auth.models import User, Group
from members.models import Wilayah, Lingkungan, Member
from payments.models import PaymentType, Payment
from datetime import date
from django.utils import timezone


class ReportViewTest(TestCase):
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
        self.pt = PaymentType.objects.get(name='Asuransi Kematian')
        Payment.objects.create(
            member=self.member, payment_type=self.pt, amount=50000,
            date_paid=timezone.now(), period_month=6, period_year=2026,
            recorded_by=self.user)

    def test_monthly_report_200(self):
        response = self.client.get('/reports/monthly/?month=6&year=2026')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Budi')

    def test_annual_report_200(self):
        response = self.client.get('/reports/annual/?year=2026')
        self.assertEqual(response.status_code, 200)

    def test_unpaid_report_200(self):
        response = self.client.get('/reports/unpaid/?month=6&year=2026&payment_type=' + str(self.pt.pk))
        self.assertEqual(response.status_code, 200)

    def test_monthly_excel_export_returns_xlsx(self):
        response = self.client.get('/reports/export/monthly/?month=6&year=2026')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'],
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_unpaid_excel_shows_member_who_did_not_pay(self):
        w = Wilayah.objects.create(name='W2')
        l = Lingkungan.objects.create(name='L2', wilayah=w)
        unpaid_member = Member.objects.create(
            member_id='002', full_name='Sari', gender='F',
            join_date=date.today(), lingkungan=l)
        response = self.client.get(f'/reports/unpaid/?month=6&year=2026&payment_type={self.pt.pk}')
        self.assertContains(response, 'Sari')
        self.assertNotContains(response, 'Budi')
