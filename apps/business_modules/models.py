from django.db import models
from apps.core.models import BaseModel


class BusinessModule(BaseModel):
    """
    Defines a business module (e.g. Hotel, Restaurant, School).
    Each module has a set of features/dashboard sections that are enabled
    when a business selects this module.
    """
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['sort_order']


class ModuleFeature(BaseModel):
    """
    A feature/dashboard section within a business module.
    e.g. Hotel module has: Rooms, Bookings, Guests, Payments, Housekeeping, Reports
    """
    module = models.ForeignKey(BusinessModule, on_delete=models.CASCADE, related_name='features')
    code = models.CharField(max_length=50)
    label = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, null=True)
    route = models.CharField(max_length=100, blank=True, null=True)
    sort_order = models.IntegerField(default=0)
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.module.name} - {self.label}"

    class Meta:
        ordering = ['sort_order']
        unique_together = ('module', 'code')


class BusinessModuleConfig(BaseModel):
    """
    Links a Business to a BusinessModule with its specific configuration.
    A business can only have one active module at a time.
    """
    business = models.OneToOneField('accounts.Business', on_delete=models.CASCADE, related_name='module_config')
    module = models.ForeignKey(BusinessModule, on_delete=models.PROTECT)
    enabled_features = models.JSONField(default=list, blank=True)
    config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.business.business_name} - {self.module.name}"
