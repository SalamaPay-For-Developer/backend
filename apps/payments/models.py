from django.db import models
from apps.core.models import BaseModel
from django.utils import timezone

class PaymentCategory(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    name_sw = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255)
    is_mandatory_electronic = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name_en} ({self.code})"

    class Meta:
        verbose_name_plural = "Payment Categories"

class Transaction(BaseModel):
    class Type(models.TextChoices):
        COLLECTION = 'COLLECTION', 'Collection (In)'
        PAYOUT = 'PAYOUT', 'Payout (Out)'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        REVERSED = 'REVERSED', 'Reversed'
        EXPIRED = 'EXPIRED', 'Expired'

    class Channel(models.TextChoices):
        MPESA = 'MPESA', 'M-Pesa'
        TIGOPESA = 'TIGOPESA', 'Tigo Pesa'
        AIRTEL = 'AIRTEL', 'Airtel Money'
        HALOPESA = 'HALOPESA', 'Halo Pesa'
        CARD = 'CARD', 'Card'
        BANK = 'BANK', 'Bank Transfer'

    reference = models.CharField(max_length=50, unique=True)
    business = models.ForeignKey('accounts.Business', on_delete=models.PROTECT, related_name='transactions', null=True, blank=True)
    customer = models.ForeignKey('accounts.User', on_delete=models.PROTECT, null=True, blank=True, related_name='transactions')
    category = models.ForeignKey(PaymentCategory, on_delete=models.PROTECT, null=True, blank=True)
    type = models.CharField(max_length=20, choices=Type.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='TZS')
    channel = models.CharField(max_length=20, choices=Channel.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Selcom specific fields
    selcom_order_id = models.CharField(max_length=100, blank=True, null=True)
    selcom_transid = models.CharField(max_length=100, blank=True, null=True)
    payment_token = models.CharField(max_length=255, blank=True, null=True)
    checkout_url = models.URLField(max_length=500, blank=True, null=True)
    
    payer_msisdn = models.CharField(max_length=15, blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Payout (disbursement) specific fields
    recipient_name = models.CharField(max_length=255, blank=True, null=True)
    recipient_phone = models.CharField(max_length=15, blank=True, null=True)
    recipient_bank = models.CharField(max_length=20, blank=True, null=True)
    recipient_account = models.CharField(max_length=50, blank=True, null=True)
    narration = models.CharField(max_length=500, blank=True, null=True)
    fee_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    webhook_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.reference} - {self.amount} {self.currency} ({self.status})"

    def mark_success(self, selcom_transid=None):
        self.status = self.Status.SUCCESS
        self.selcom_transid = selcom_transid
        self.completed_at = timezone.now()
        self.save()
        
    def mark_failed(self, reason):
        self.status = self.Status.FAILED
        self.failure_reason = reason
        self.save()
