from django.db import models
from apps.core.models import BaseModel

class WebhookEvent(BaseModel):
    class Provider(models.TextChoices):
        SELCOM = 'SELCOM', 'Selcom'

    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.SELCOM)
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    signature = models.TextField(blank=True, null=True)
    processed = models.BooleanField(default=False)
    related_transaction = models.ForeignKey('payments.Transaction', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.provider} - {self.event_type} ({self.id})"
