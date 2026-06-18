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
    member = models.ForeignKey('members.Member', on_delete=models.PROTECT, related_name='payments')
    payment_type = models.ForeignKey(PaymentType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateTimeField()
    period_month = models.IntegerField()
    period_year = models.IntegerField()
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        return f'{self.member.full_name} — {self.period_month}/{self.period_year}'
