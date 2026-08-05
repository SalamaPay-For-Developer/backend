from django.core.management.base import BaseCommand
from apps.business_modules.models import BusinessModule, ModuleFeature

class Command(BaseCommand):
    help = 'Seed business modules and their dashboard features'

    MODULES = [
        {
            'code': 'RESTAURANT',
            'name': 'Restaurant',
            'icon': 'utensils',
            'features': [
                ('ORDERS', 'Orders', 'shopping-bag', '/orders', 1),
                ('TABLES', 'Tables', 'layout-grid', '/tables', 2),
                ('QR_CODES', 'QR Codes', 'qr-code', '/qr-codes', 3),
                ('KITCHEN', 'Kitchen', 'chef-hat', '/kitchen', 4),
                ('WAITERS', 'Waiters', 'users', '/waiters', 5),
                ('PAYMENTS', 'Payments', 'credit-card', '/payments', 6),
                ('REPORTS', 'Reports', 'bar-chart', '/reports', 7),
            ],
        },
        {
            'code': 'HOTEL',
            'name': 'Hotel',
            'icon': 'building',
            'features': [
                ('ROOMS', 'Rooms', 'door-open', '/rooms', 1),
                ('BOOKINGS', 'Bookings', 'calendar', '/bookings', 2),
                ('GUESTS', 'Guests', 'users', '/guests', 3),
                ('PAYMENTS', 'Payments', 'credit-card', '/payments', 4),
                ('HOUSEKEEPING', 'Housekeeping', 'sparkles', '/housekeeping', 5),
                ('REPORTS', 'Reports', 'bar-chart', '/reports', 6),
            ],
        },
        {
            'code': 'SCHOOL',
            'name': 'School',
            'icon': 'graduation-cap',
            'features': [
                ('STUDENTS', 'Students', 'users', '/students', 1),
                ('CLASSES', 'Classes', 'book-open', '/classes', 2),
                ('FEES', 'Fees', 'wallet', '/fees', 3),
                ('PAYMENTS', 'Payments', 'credit-card', '/payments', 4),
                ('RECEIPTS', 'Receipts', 'file-text', '/receipts', 5),
                ('REPORTS', 'Reports', 'bar-chart', '/reports', 6),
            ],
        },
        {
            'code': 'PHARMACY',
            'name': 'Pharmacy',
            'icon': 'pill',
            'features': [
                ('MEDICINES', 'Medicines', 'pill', '/medicines', 1),
                ('INVENTORY', 'Inventory', 'package', '/inventory', 2),
                ('SALES', 'Sales', 'shopping-bag', '/sales', 3),
                ('PAYMENTS', 'Payments', 'credit-card', '/payments', 4),
                ('REPORTS', 'Reports', 'bar-chart', '/reports', 5),
            ],
        },
        {
            'code': 'FUEL_STATION',
            'name': 'Fuel Station',
            'icon': 'fuel',
            'features': [
                ('PUMPS', 'Pumps', 'fuel', '/pumps', 1),
                ('SALES', 'Sales', 'shopping-bag', '/sales', 2),
                ('TRANSACTIONS', 'Transactions', 'arrow-left-right', '/transactions', 3),
                ('REPORTS', 'Reports', 'bar-chart', '/reports', 4),
            ],
        },
        {
            'code': 'TRANSPORT',
            'name': 'Transport',
            'icon': 'bus',
            'features': [
                ('ROUTES', 'Routes', 'map-pin', '/routes', 1),
                ('TICKETS', 'Tickets', 'ticket', '/tickets', 2),
                ('PASSENGERS', 'Passengers', 'users', '/passengers', 3),
                ('PAYMENTS', 'Payments', 'credit-card', '/payments', 4),
            ],
        },
        {
            'code': 'PROPERTY',
            'name': 'Property',
            'icon': 'home',
            'features': [
                ('HOUSES', 'Houses', 'home', '/houses', 1),
                ('TENANTS', 'Tenants', 'users', '/tenants', 2),
                ('RENT', 'Rent', 'wallet', '/rent', 3),
                ('PAYMENTS', 'Payments', 'credit-card', '/payments', 4),
            ],
        },
        {
            'code': 'RETAIL_SHOP',
            'name': 'Retail Shop',
            'icon': 'shopping-cart',
            'features': [
                ('PRODUCTS', 'Products', 'package', '/products', 1),
                ('POS', 'POS', 'scan-barcode', '/pos', 2),
                ('CUSTOMERS', 'Customers', 'users', '/customers', 3),
                ('PAYMENTS', 'Payments', 'credit-card', '/payments', 4),
                ('REPORTS', 'Reports', 'bar-chart', '/reports', 5),
            ],
        },
    ]

    def handle(self, *args, **kwargs):
        for idx, mod_data in enumerate(self.MODULES):
            module, created = BusinessModule.objects.get_or_create(
                code=mod_data['code'],
                defaults={
                    'name': mod_data['name'],
                    'icon': mod_data['icon'],
                    'sort_order': idx,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created module: {mod_data["name"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'Module already exists: {mod_data["name"]}'))

            for feat in mod_data['features']:
                obj, feat_created = ModuleFeature.objects.get_or_create(
                    module=module,
                    code=feat[0],
                    defaults={
                        'label': feat[1],
                        'icon': feat[2],
                        'route': feat[3],
                        'sort_order': feat[4],
                    }
                )
                if feat_created:
                    self.stdout.write(self.style.SUCCESS(f'  + Feature: {feat[1]}'))
