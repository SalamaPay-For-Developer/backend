from django.core.management.base import BaseCommand
from apps.payments.models import PaymentCategory

class Command(BaseCommand):
    help = 'Seed 9 mandatory electronic payment categories'

    def handle(self, *args, **kwargs):
        categories = [
            {'code': 'TRANSPORT', 'sw': 'Usafirishaji', 'en': 'Transport'},
            {'code': 'MALLS_ENTERTAINMENT', 'sw': 'Maduka Makubwa na Burudani', 'en': 'Malls and Entertainment'},
            {'code': 'EDUCATION', 'sw': 'Elimu (Ada)', 'en': 'Education'},
            {'code': 'HIGHER_EDUCATION', 'sw': 'Elimu ya Juu', 'en': 'Higher Education'},
            {'code': 'HOSPITALITY', 'sw': 'Huduma za Hoteli na Migahawa', 'en': 'Hospitality'},
            {'code': 'TOURISM', 'sw': 'Utalii', 'en': 'Tourism'},
            {'code': 'REAL_ESTATE', 'sw': 'Ardhi na Nyumba', 'en': 'Real Estate'},
            {'code': 'VEHICLES', 'sw': 'Magari', 'en': 'Vehicles'},
            {'code': 'AGRICULTURE', 'sw': 'Kilimo na Vyama vya Ushirika', 'en': 'Agriculture'},
        ]

        for cat in categories:
            obj, created = PaymentCategory.objects.get_or_create(
                code=cat['code'],
                defaults={
                    'name_sw': cat['sw'],
                    'name_en': cat['en'],
                    'is_mandatory_electronic': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {cat["code"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'Category already exists: {cat["code"]}'))
