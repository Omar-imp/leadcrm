import datetime
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from leads.models import SalesPerson, Lead, FollowUp


class Command(BaseCommand):
    help = "Seed the database with a demo admin user, an SPO, and sample leads."

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin12345')
            self.stdout.write(self.style.SUCCESS('Created superuser "admin" / "admin12345"'))

        spo_user, _ = User.objects.get_or_create(username='arbaz')
        spo_user.set_password('arbaz12345')
        spo_user.save()
        spo, _ = SalesPerson.objects.get_or_create(name='Arbaz', user=spo_user)

        sources = ['advertisement', 'facebook', 'whatsapp', 'website', 'walkin']
        statuses = ['new', 'positive', 'lost', 'quotation', 'converted']

        if Lead.objects.count() < 5:
            for i in range(12):
                lead = Lead.objects.create(
                    lead_source=random.choice(sources),
                    name=f"Sample Lead {i + 1}",
                    contact_number=f"0300000{i:04d}",
                    email=f"lead{i}@example.com",
                    city="Karachi",
                    country="Pakistan",
                    quotation=random.choice([0, 5000, 10000]),
                    status=random.choice(statuses),
                    spo=spo,
                )
                FollowUp.objects.create(
                    lead=lead,
                    follow_up_date=timezone.now() + datetime.timedelta(days=random.choice([-1, 0, 1, 2])),
                    status=random.choice(['pending', 'done']),
                )
            self.stdout.write(self.style.SUCCESS('Seeded 12 sample leads.'))
        else:
            self.stdout.write('Leads already exist, skipping.')