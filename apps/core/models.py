import uuid
from django.db import models

class BaseModel(models.Model):
    """
    NOTE: apps.core.idempotency.IdempotencyRecord also lives in this app
    and is imported at the bottom of this file so Django's migration
    autodetector picks it up.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SMSLog(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'

    phone = models.CharField(max_length=20)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    response = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"SMS to {self.phone} - {self.status}"


class IdempotencyRecord(BaseModel):
    """
    Stores cached responses for POST requests sent with an Idempotency-Key
    header, per the SalamaPay/Snippe idempotency contract (24h TTL, max 30
    character keys). See apps.core.idempotency for the request-handling logic.
    """
    key = models.CharField(max_length=64, db_index=True)
    endpoint = models.CharField(max_length=255)
    request_hash = models.CharField(max_length=64)
    response_status = models.IntegerField()
    response_body = models.JSONField()
    expires_at = models.DateTimeField()

    class Meta:
        unique_together = ('key', 'endpoint')

    def __str__(self):
        return f"Idempotency({self.key}) -> {self.endpoint}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
