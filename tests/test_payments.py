from django.test import TestCase
from django.contrib.auth.models import User
from members.models import Wilayah, Lingkungan, Member
from payments.models import Payment, PaymentType
from datetime import date
from django.utils import timezone


class PaymentTypeModelTest(TestCase):
    def test_correct_types_exist(self):
        PaymentType.objects.get_or_create(name='Iuran PKSS', defaults={'is_active': True})
        PaymentType.objects.get_or_create(name='Iuran Kartu Kuning', defaults={'is_active': True})
        names = list(PaymentType.objects.filter(is_active=True).values_list('name', flat=True))
        self.assertIn('Iuran PKSS', names)
        self.assertIn('Iuran Kartu Kuning', names)


class PaymentModelTest(TestCase):
    def setUp(self):
        w = Wilayah.objects.create(name='W1')
        l = Lingkungan.objects.create(name='L1', wilayah=w)
        self.member = Member.objects.create(
            member_id='001', full_name='Budi', gender='M',
            join_date=date.today(), lingkungan=l)
        self.pt, _ = PaymentType.objects.get_or_create(
            name='Iuran PKSS', defaults={'is_active': True})
        self.user = User.objects.create_user('u', password='pass')

    def test_payment_str(self):
        p = Payment.objects.create(
            member=self.member, payment_type=self.pt, amount=50000,
            date_received=timezone.now(), period_month=6, period_year=2026,
            recorded_by=self.user)
        self.assertIn('Budi', str(p))
        self.assertIn('6/2026', str(p))

    def test_advance_payment_different_period(self):
        p = Payment.objects.create(
            member=self.member, payment_type=self.pt, amount=50000,
            date_received=timezone.now(), period_month=1, period_year=2026,
            recorded_by=self.user)
        self.assertEqual(p.period_month, 1)
        self.assertNotEqual(p.date_received.month, p.period_month)


class RecordPaymentViewTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Group
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

    def test_get_record_payment_page(self):
        response = self.client.get('/payments/new/')
        self.assertEqual(response.status_code, 200)

    def test_post_creates_payment(self):
        now = timezone.localtime(timezone.now())
        response = self.client.post('/payments/new/', {
            'member_id': self.member.pk,
            'payment_type': self.pt.pk,
            'amount': '50000',
            'date_received': now.strftime('%Y-%m-%dT%H:%M'),
            'period_month': '6',
            'period_year': '2026',
            'notes': '',
        })
        self.assertRedirects(response, '/payments/')
        self.assertEqual(Payment.objects.count(), 1)

    def test_payment_list_returns_200(self):
        response = self.client.get('/payments/')
        self.assertEqual(response.status_code, 200)
