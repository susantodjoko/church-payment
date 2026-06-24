from django.db import migrations


def rename_pkss_to_pkks(apps, schema_editor):
    PaymentType = apps.get_model('payments', 'PaymentType')
    PaymentType.objects.filter(name='Iuran PKSS').update(name='Iuran PKKS')


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0005_payment_must_have_member_or_keluarga'),
    ]

    operations = [
        migrations.RunPython(rename_pkss_to_pkks, migrations.RunPython.noop),
    ]
