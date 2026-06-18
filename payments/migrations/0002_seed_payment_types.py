from django.db import migrations


def seed_payment_types(apps, schema_editor):
    PaymentType = apps.get_model('payments', 'PaymentType')
    defaults = [
        {'name': 'Asuransi Kematian', 'description': 'Iuran asuransi kematian bulanan', 'is_default': True},
        {'name': 'Persepuluhan', 'description': 'Persembahan persepuluhan', 'is_default': True},
        {'name': 'Persembahan', 'description': 'Persembahan umum', 'is_default': True},
    ]
    for d in defaults:
        PaymentType.objects.get_or_create(name=d['name'], defaults=d)


class Migration(migrations.Migration):
    dependencies = [('payments', '0001_initial')]

    operations = [
        migrations.RunPython(seed_payment_types, migrations.RunPython.noop),
    ]
