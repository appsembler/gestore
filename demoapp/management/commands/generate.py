import sys

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from demoapp.factories.demoapp import BookInstanceFactory


class Command(BaseCommand):
    help = 'Generates objects in the database'

    def handle(self, *args, **options):
        self.stdout.write('Generating instances in progress...')

        self.create_superuser()
        self.generate_books_instances()

        self.stdout.write(self.style.SUCCESS(
            'Objects generated successfully!'
        ))

    def generate_books_instances(self):
        for _ in range(1000):
            self.stdout.write('.', ending='')
            sys.stdout.flush()

            BookInstanceFactory.create()
        self.stdout.write()

    @staticmethod
    def create_superuser():
        User.objects.create_superuser(
            username='admin',
            email='admin@appsembler.com',
            password='admin'
        )
