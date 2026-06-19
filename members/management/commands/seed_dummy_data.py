import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from members.models import Keluarga, Lingkungan, Member, Wilayah
from payments.models import Payment, PaymentType


WILAYAH_DATA = [
    "Wilayah Utara",
    "Wilayah Selatan",
    "Wilayah Timur",
    "Wilayah Barat",
    "Wilayah Tengah",
]

LINGKUNGAN_DATA = [
    ("Lingkungan Santo Petrus", "Wilayah Utara"),
    ("Lingkungan Santo Paulus", "Wilayah Selatan"),
    ("Lingkungan Santo Yohanes", "Wilayah Timur"),
    ("Lingkungan Santa Maria", "Wilayah Barat"),
    ("Lingkungan Santo Yusuf", "Wilayah Tengah"),
]

KK_DATA = [
    ("KK001", "Keluarga Hartono",        "Lingkungan Santo Petrus"),
    ("KK002", "Keluarga Kusuma",          "Lingkungan Santo Petrus"),
    ("KK003", "Keluarga Santoso",         "Lingkungan Santo Petrus"),
    ("KK004", "Keluarga Wijaya",          "Lingkungan Santo Paulus"),
    ("KK005", "Keluarga Setiawan",        "Lingkungan Santo Paulus"),
    ("KK006", "Keluarga Lestari",         "Lingkungan Santo Paulus"),
    ("KK007", "Keluarga Purnomo",         "Lingkungan Santo Yohanes"),
    ("KK008", "Keluarga Rahayu",          "Lingkungan Santo Yohanes"),
    ("KK009", "Keluarga Suryadi",         "Lingkungan Santo Yohanes"),
    ("KK010", "Keluarga Wahyuni",         "Lingkungan Santa Maria"),
    ("KK011", "Keluarga Budiman",         "Lingkungan Santa Maria"),
    ("KK012", "Keluarga Anggraini",       "Lingkungan Santa Maria"),
    ("KK013", "Keluarga Wibowo",          "Lingkungan Santo Yusuf"),
    ("KK014", "Keluarga Pratiwi",         "Lingkungan Santo Yusuf"),
    ("KK015", "Keluarga Susanto",         "Lingkungan Santo Yusuf"),
]

MEMBERS_DATA = [
    ("Agustinus Hartono", "M", "1975-03-12"),
    ("Bernadette Kusuma", "F", "1982-07-25"),
    ("Carolus Santoso", "M", "1968-11-08"),
    ("Dorothea Wijaya", "F", "1990-04-17"),
    ("Emanuel Setiawan", "M", "1985-09-30"),
    ("Fransisca Lestari", "F", "1978-01-14"),
    ("Gregorius Purnomo", "M", "1972-06-22"),
    ("Helena Rahayu", "F", "1995-08-05"),
    ("Ignatius Suryadi", "M", "1960-12-19"),
    ("Johanna Wahyuni", "F", "1988-02-28"),
    ("Kristoforus Budiman", "M", "1979-05-11"),
    ("Lucia Anggraini", "F", "1993-10-03"),
    ("Martinus Wibowo", "M", "1965-07-16"),
    ("Natalia Pratiwi", "F", "1987-03-09"),
    ("Ongkos Susanto", "M", "1970-11-27"),
    ("Paulina Handayani", "F", "1983-06-01"),
    ("Quirinus Darmawan", "M", "1958-09-14"),
    ("Rosa Indrawati", "F", "1991-12-08"),
    ("Stefanus Gunawan", "M", "1976-04-23"),
    ("Theresia Oktaviani", "F", "1996-08-31"),
    ("Urbanus Kurniawan", "M", "1963-01-07"),
    ("Veronika Astuti", "F", "1989-05-20"),
    ("Wilhelmus Saputra", "M", "1974-10-13"),
    ("Xaveria Melinda", "F", "1984-02-04"),
    ("Yohanes Kristanto", "M", "1967-07-18"),
    ("Zefirinus Cahyono", "M", "1980-03-26"),
    ("Alexius Nugroho", "M", "1992-11-09"),
    ("Brigida Sari", "F", "1973-06-15"),
    ("Calistus Priyono", "M", "1986-09-02"),
    ("Damiana Purwanto", "F", "1997-01-21"),
    ("Eustakius Hermawan", "M", "1961-04-07"),
    ("Faustina Dewi", "F", "1994-08-19"),
    ("Genoveva Sutrisno", "F", "1977-12-30"),
    ("Hendrikus Irawan", "M", "1969-05-06"),
    ("Imelda Kurnia", "F", "1990-10-24"),
    ("Januarius Wahyu", "M", "1981-02-11"),
    ("Klara Ningrum", "F", "1985-07-03"),
    ("Laurensius Hadi", "M", "1955-11-17"),
    ("Magdalena Putri", "F", "1998-03-28"),
    ("Nikolaus Prasetyo", "M", "1971-06-09"),
    ("Oktavia Suharto", "F", "1988-01-16"),
    ("Petronella Sanjaya", "F", "1966-04-29"),
    ("Redemptus Firmanto", "M", "1983-09-11"),
    ("Silvester Mukti", "M", "1975-12-22"),
    ("Tarsisia Wahab", "F", "1993-05-07"),
    ("Ulrikus Handoko", "M", "1959-08-14"),
    ("Valentina Sukma", "F", "1987-02-25"),
    ("Walburgis Ratnasari", "F", "1979-07-08"),
    ("Xystus Pramono", "M", "1964-10-19"),
    ("Yuliana Setiadi", "F", "1995-04-01"),
]


class Command(BaseCommand):
    help = "Seed dummy data: 5 wilayah, 5 lingkungan, 50 members with payments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            Payment.objects.all().delete()
            Member.objects.all().delete()
            Keluarga.objects.all().delete()
            Lingkungan.objects.all().delete()
            Wilayah.objects.all().delete()

        # Create Wilayah
        self.stdout.write("Creating 5 wilayah...")
        wilayah_map = {}
        for name in WILAYAH_DATA:
            w, created = Wilayah.objects.get_or_create(name=name)
            wilayah_map[name] = w
            if created:
                self.stdout.write(f"  + {name}")

        # Create Lingkungan
        self.stdout.write("Creating 5 lingkungan...")
        lingkungan_map = {}
        for ling_name, wil_name in LINGKUNGAN_DATA:
            l, created = Lingkungan.objects.get_or_create(
                name=ling_name, wilayah=wilayah_map[wil_name]
            )
            lingkungan_map[ling_name] = l
            if created:
                self.stdout.write(f"  + {ling_name} ({wil_name})")

        # Create Keluarga (KK)
        self.stdout.write("Creating 15 keluarga (KK)...")
        kk_map = {}
        for kk_number, kk_name, ling_name in KK_DATA:
            kk, created = Keluarga.objects.get_or_create(
                kk_number=kk_number,
                defaults=dict(
                    name=kk_name,
                    lingkungan=lingkungan_map[ling_name],
                    is_active=True,
                ),
            )
            kk_map[kk_number] = kk
            if created:
                self.stdout.write(f"  + {kk_number} {kk_name}")

        # Create Members (10 per lingkungan)
        self.stdout.write("Creating 50 members...")
        lingkungan_list = list(lingkungan_map.values())
        members_created = 0
        for i, (full_name, gender, dob_str) in enumerate(MEMBERS_DATA):
            lingkungan = lingkungan_list[i % len(lingkungan_list)]
            member_id = f"JMT{str(i + 1).zfill(4)}"
            dob = date.fromisoformat(dob_str)
            join_year = random.randint(2000, 2020)
            join_date = date(join_year, random.randint(1, 12), random.randint(1, 28))
            address_num = random.randint(1, 99)
            address = f"Jl. Gereja No. {address_num}, {lingkungan.wilayah.name}"
            phone = f"08{random.randint(100000000, 999999999)}"
            _, created = Member.objects.get_or_create(
                member_id=member_id,
                defaults=dict(
                    full_name=full_name,
                    gender=gender,
                    date_of_birth=dob,
                    address=address,
                    phone=phone,
                    join_date=join_date,
                    lingkungan=lingkungan,
                    is_active=True,
                ),
            )
            if created:
                members_created += 1
        self.stdout.write(f"  Created {members_created} members")

        # Assign members to KK (round-robin within same lingkungan)
        self.stdout.write("Assigning members to Keluarga...")
        assigned = 0
        for ling_obj in lingkungan_map.values():
            ling_members = list(
                Member.objects.filter(lingkungan=ling_obj, keluarga=None)
            )
            ling_kk = list(
                Keluarga.objects.filter(lingkungan=ling_obj, is_active=True)
            )
            if not ling_kk:
                continue
            for i, member in enumerate(ling_members):
                member.keluarga = ling_kk[i % len(ling_kk)]
                member.save(update_fields=['keluarga'])
                assigned += 1
        self.stdout.write(f"  Assigned {assigned} members to Keluarga")

        # Seed payments for the last 6 months
        recorder = User.objects.filter(is_superuser=True).first()
        if not recorder:
            recorder = User.objects.filter(is_staff=True).first()

        if not recorder:
            self.stdout.write(
                self.style.WARNING(
                    "No superuser found — skipping payment seeding. "
                    "Run 'createsuperuser' first, then re-run this command."
                )
            )
            self.stdout.write(self.style.SUCCESS("Done (without payments)."))
            return

        # Ensure only the two correct payment types are active
        PaymentType.objects.exclude(
            name__in=['Iuran PKSS', 'Iuran Kartu Kuning']
        ).update(is_active=False)
        pkss, _ = PaymentType.objects.get_or_create(
            name='Iuran PKSS',
            defaults={'description': 'Iuran PKSS per anggota', 'is_active': True}
        )
        if not pkss.is_active:
            pkss.is_active = True
            pkss.save()
        kartu_kuning, _ = PaymentType.objects.get_or_create(
            name='Iuran Kartu Kuning',
            defaults={'description': 'Iuran Kartu Kuning per KK', 'is_active': True}
        )
        if not kartu_kuning.is_active:
            kartu_kuning.is_active = True
            kartu_kuning.save()

        self.stdout.write("Creating payments for last 6 months...")
        today = date.today()
        payments_created = 0
        for member in Member.objects.all():
            for months_ago in range(6):
                month = today.month - months_ago
                year = today.year
                if month <= 0:
                    month += 12
                    year -= 1
                if Payment.objects.filter(
                    member=member, keluarga=None, payment_type=pkss,
                    period_month=month, period_year=year
                ).exists():
                    continue
                amount = Decimal(str(random.choice([50000, 75000, 100000, 150000, 200000])))
                pay_day = random.randint(1, 28)
                date_received = timezone.make_aware(
                    timezone.datetime(year, month, pay_day, 9, 0)
                )
                Payment.objects.create(
                    member=member,
                    keluarga=None,
                    payment_type=pkss,
                    amount=amount,
                    date_received=date_received,
                    period_month=month,
                    period_year=year,
                    recorded_by=recorder,
                )
                payments_created += 1

        self.stdout.write(f"  Created {payments_created} PKSS payments")

        # Seed Iuran Kartu Kuning for each KK for last 6 months
        self.stdout.write("Creating Kartu Kuning payments for KK...")
        kk_payments_created = 0
        for kk in Keluarga.objects.filter(is_active=True):
            for months_ago in range(6):
                month = today.month - months_ago
                year = today.year
                if month <= 0:
                    month += 12
                    year -= 1
                if Payment.objects.filter(
                    keluarga=kk, member=None, payment_type=kartu_kuning,
                    period_month=month, period_year=year
                ).exists():
                    continue
                amount = Decimal('50000')
                pay_day = random.randint(1, 28)
                date_received = timezone.make_aware(
                    timezone.datetime(year, month, pay_day, 10, 0)
                )
                Payment.objects.create(
                    member=None,
                    keluarga=kk,
                    payment_type=kartu_kuning,
                    amount=amount,
                    date_received=date_received,
                    period_month=month,
                    period_year=year,
                    recorded_by=recorder,
                )
                kk_payments_created += 1

        self.stdout.write(f"  Created {kk_payments_created} Kartu Kuning payments")
        self.stdout.write(self.style.SUCCESS("Dummy data seeded successfully!"))
