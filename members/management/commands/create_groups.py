from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Create Super Admin and Treasurer groups'

    def handle(self, *args, **options):
        Group.objects.get_or_create(name='Super Admin')
        Group.objects.get_or_create(name='Treasurer')
        self.stdout.write(self.style.SUCCESS('Groups created: Super Admin, Treasurer'))
