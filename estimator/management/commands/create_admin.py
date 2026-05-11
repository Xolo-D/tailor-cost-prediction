"""
Management command: python manage.py create_admin
Creates a default admin/superuser for the system.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from estimator.models import TailorProfile


class Command(BaseCommand):
    help = 'Create a default admin superuser for the Tailor Cost System'

    def add_arguments(self, parser):
        parser.add_argument('--email',    default='admin@unizulu.ac.za')
        parser.add_argument('--password', default='admin1234')
        parser.add_argument('--first',    default='Admin')
        parser.add_argument('--last',     default='User')

    def handle(self, *args, **options):
        email    = options['email']
        password = options['password']

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Admin {email} already exists.'))
            return

        user = User.objects.create_superuser(
            username   = email,
            email      = email,
            password   = password,
            first_name = options['first'],
            last_name  = options['last'],
        )
        TailorProfile.objects.get_or_create(user=user)
        self.stdout.write(self.style.SUCCESS(
            f'✓ Admin created: {email} / {password}'
        ))
