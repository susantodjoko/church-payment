from django.db import models
from django.contrib.auth.models import User


class PaymentType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Payment(models.Model):
    member = models.ForeignKey(
        'members.Member', on_delete=models.PROTECT,
        related_name='payments', null=True, blank=True
    )
    keluarga = models.ForeignKey(
        'members.Keluarga', on_delete=models.PROTECT,
        related_name='payments', null=True, blank=True
    )
    payment_type = models.ForeignKey(PaymentType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_received = models.DateTimeField()
    period_month = models.IntegerField()
    period_year = models.IntegerField()
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='recorded_payments')
    notes = models.TextField(null=True, blank=True)
    date_reported = models.DateTimeField(null=True, blank=True)
    date_confirmed = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True, related_name='confirmed_payments'
    )

    class Meta:
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        subject = self.member.full_name if self.member else str(self.keluarga)
        return f'{subject} — {self.period_month}/{self.period_year}'

    @property
    def is_reported(self):
        return self.date_reported is not None

    @property
    def is_confirmed(self):
        return self.date_confirmed is not None
