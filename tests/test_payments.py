from django.test import TestCase
from payments.models import PaymentType


class PaymentTypeModelTest(TestCase):
    def test_default_types_exist_after_migration(self):
        names = list(PaymentType.objects.values_list('name', flat=True))
        self.assertIn('Asuransi Kematian', names)
        self.assertIn('Persepuluhan', names)
        self.assertIn('Persembahan', names)

    def test_default_types_cannot_be_deleted_flag(self):
        pt = PaymentType.objects.get(name='Asuransi Kematian')
        self.assertTrue(pt.is_default)
