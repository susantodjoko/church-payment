from django.db import models


class Wilayah(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'Wilayah'
        ordering = ['name']

    def __str__(self):
        return self.name


class Lingkungan(models.Model):
    name = models.CharField(max_length=100)
    wilayah = models.ForeignKey(Wilayah, on_delete=models.PROTECT, related_name='lingkungan_set')

    class Meta:
        verbose_name_plural = 'Lingkungan'
        ordering = ['wilayah__name', 'name']

    def __str__(self):
        return f'{self.name} ({self.wilayah.name})'


class Member(models.Model):
    GENDER_CHOICES = [('M', 'Laki-laki'), ('F', 'Perempuan')]

    member_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=255)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    join_date = models.DateField()
    lingkungan = models.ForeignKey(Lingkungan, on_delete=models.PROTECT, related_name='members')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.member_id})'
