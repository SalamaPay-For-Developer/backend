import uuid
import secrets
import string
from django.db import models
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from apps.core.models import BaseModel
from apps.accounts.models import Business


class DeveloperWorkspace(BaseModel):
    class Environment(models.TextChoices):
        SANDBOX = 'SANDBOX', 'Sandbox'
        PRODUCTION = 'PRODUCTION', 'Production'

    class SetupStep(models.TextChoices):
        BUSINESS = 'BUSINESS', 'Business Profile'
        KYC = 'KYC', 'KYC Verification'
        SELCOM = 'SELCOM', 'Connect Selcom'
        WEBHOOK = 'WEBHOOK', 'Configure Webhook'
        TEST = 'TEST', 'Test Transaction'
        PRODUCTION_APPROVAL = 'PRODUCTION_APPROVAL', 'Production Approval'

    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name='developer_workspace')
    environment = models.CharField(max_length=20, choices=Environment.choices, default=Environment.SANDBOX)
    production_enabled = models.BooleanField(default=False)
    production_approved_at = models.DateTimeField(null=True, blank=True)

    # Setup checklist
    selcom_connected = models.BooleanField(default=False)
    webhook_configured = models.BooleanField(default=False)
    test_completed = models.BooleanField(default=False)

    # Metadata
    allowed_domains = models.JSONField(default=list, blank=True)
    ip_allowlist = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Developer Workspace - {self.business.business_name}"

    @property
    def is_production_ready(self):
        return (
            self.business.is_verified
            and self.selcom_connected
            and self.webhook_configured
            and self.test_completed
            and self.production_enabled
        )

    @property
    def setup_progress(self):
        steps = [
            self.business.is_verified,
            self.selcom_connected,
            self.webhook_configured,
            self.test_completed,
        ]
        completed = sum(1 for s in steps if s)
        return {
            'completed': completed,
            'total': len(steps),
            'percentage': int((completed / len(steps)) * 100),
            'steps': {
                'business': self.business.is_verified,
                'kyc': self.business.is_verified,
                'selcom': self.selcom_connected,
                'webhook': self.webhook_configured,
                'test': self.test_completed,
                'production': self.production_enabled,
            }
        }


class SelcomCredential(BaseModel):
    class Environment(models.TextChoices):
        SANDBOX = 'SANDBOX', 'Sandbox'
        PRODUCTION = 'PRODUCTION', 'Production'

    workspace = models.ForeignKey(DeveloperWorkspace, on_delete=models.CASCADE, related_name='selcom_credentials')
    environment = models.CharField(max_length=20, choices=Environment.choices)
    api_key = models.CharField(max_length=255)
    api_secret_encrypted = models.TextField()
    vendor_id = models.CharField(max_length=100, blank=True, null=True)
    pin = models.CharField(max_length=255, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    last_check_status = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        unique_together = ('workspace', 'environment')

    def set_api_secret(self, raw_secret):
        self.api_secret_encrypted = make_password(raw_secret)

    def check_api_secret(self, raw_secret):
        return check_password(raw_secret, self.api_secret_encrypted)

    @property
    def masked_api_key(self):
        if len(self.api_key) <= 8:
            return '•' * len(self.api_key)
        return self.api_key[:4] + '•' * (len(self.api_key) - 8) + self.api_key[-4:]

    @property
    def masked_api_secret(self):
        return '•' * 16

    def __str__(self):
        return f"Selcom {self.environment} - {self.workspace.business.business_name}"


class SalamaPayApiKey(BaseModel):
    class KeyType(models.TextChoices):
        PUBLIC = 'PUBLIC', 'Public Key'
        SECRET = 'SECRET', 'Secret Key'
        WEBHOOK = 'WEBHOOK', 'Webhook Secret'

    class Environment(models.TextChoices):
        SANDBOX = 'SANDBOX', 'Sandbox'
        PRODUCTION = 'PRODUCTION', 'Production'

    workspace = models.ForeignKey(DeveloperWorkspace, on_delete=models.CASCADE, related_name='api_keys')
    key_type = models.CharField(max_length=20, choices=KeyType.choices)
    environment = models.CharField(max_length=20, choices=Environment.choices, default=Environment.SANDBOX)
    key_prefix = models.CharField(max_length=20)
    key_hash = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    rotated_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='rotations')

    @staticmethod
    def generate_key(environment, key_type):
        env_prefix = 'test' if environment == 'SANDBOX' else 'live'
        type_prefix = 'pk' if key_type == 'PUBLIC' else 'sk' if key_type == 'SECRET' else 'whsec'
        random_part = ''.join(secrets.choice(string.ascii_lowercase + string.digits + '_') for _ in range(32))
        return f"sp_{env_prefix}_{type_prefix}_{random_part}"

    def __str__(self):
        return f"{self.key_type} ({self.environment}) - {self.workspace.business.business_name}"


class WebhookEndpoint(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'

    workspace = models.ForeignKey(DeveloperWorkspace, on_delete=models.CASCADE, related_name='webhook_endpoints')
    url = models.URLField(max_length=500)
    description = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    events = models.JSONField(default=list)
    secret = models.CharField(max_length=255, blank=True, null=True)

    # Stats
    total_deliveries = models.IntegerField(default=0)
    successful_deliveries = models.IntegerField(default=0)
    failed_deliveries = models.IntegerField(default=0)

    @property
    def delivery_rate(self):
        if self.total_deliveries == 0:
            return 0
        return round((self.successful_deliveries / self.total_deliveries) * 100, 1)

    def __str__(self):
        return f"Webhook - {self.url[:50]}"


class WebhookDelivery(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        DELIVERED = 'DELIVERED', 'Delivered'
        FAILED = 'FAILED', 'Failed'
        RETRYING = 'RETRYING', 'Retrying'

    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempt_count = models.IntegerField(default=0)
    delivered_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    # Link to transaction if applicable
    transaction_ref = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Webhook Delivery - {self.event_type} - {self.status}"


class CheckoutSession(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        EXPIRED = 'EXPIRED', 'Expired'
        CANCELLED = 'CANCELLED', 'Cancelled'

    workspace = models.ForeignKey(DeveloperWorkspace, on_delete=models.CASCADE, related_name='checkout_sessions')
    order_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='TZS')
    description = models.TextField(blank=True, null=True)

    # Customer
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)

    # Payment methods enabled
    payment_methods = models.JSONField(default=list)

    # URLs
    success_url = models.URLField(max_length=500, blank=True, null=True)
    cancel_url = models.URLField(max_length=500, blank=True, null=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)

    # Selcom
    selcom_order_id = models.CharField(max_length=100, blank=True, null=True)
    selcom_transid = models.CharField(max_length=100, blank=True, null=True)

    # Customization
    appearance_config = models.JSONField(default=dict, blank=True)

    @property
    def checkout_url(self):
        return f"https://pay.salamapay.co/checkout/{self.order_id}"

    def __str__(self):
        return f"Checkout {self.order_id} - {self.amount} {self.currency}"


class ApiLog(BaseModel):
    workspace = models.ForeignKey(DeveloperWorkspace, on_delete=models.CASCADE, related_name='api_logs')
    method = models.CharField(max_length=10)
    endpoint = models.CharField(max_length=255)
    request_headers = models.JSONField(default=dict, blank=True)
    request_body = models.JSONField(default=dict, blank=True, null=True)
    response_status = models.IntegerField()
    response_body = models.JSONField(default=dict, blank=True, null=True)
    duration_ms = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, null=True)

    # Related transaction
    transaction_ref = models.CharField(max_length=100, blank=True, null=True)

    @property
    def is_success(self):
        return 200 <= self.response_status < 300

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.response_status}"


class ServiceCapability(BaseModel):
    class ServiceType(models.TextChoices):
        CHECKOUT = 'CHECKOUT', 'Checkout'
        C2B_COLLECTION = 'C2B_COLLECTION', 'C2B Collections'
        UTILITY_PAYMENT = 'UTILITY_PAYMENT', 'Utility Payments'
        WALLET_CASHIN = 'WALLET_CASHIN', 'Wallet Cashin'
        QWIKSEND = 'QWIKSEND', 'Qwiksend (Bank Transfer)'
        WEBHOOKS = 'WEBHOOKS', 'Webhooks'
        VCN = 'VCN', 'Virtual Card Numbers'
        IMT = 'IMT', 'International Transfer'
        GOVERNMENT = 'GOVERNMENT', 'Government Payments'

    workspace = models.ForeignKey(DeveloperWorkspace, on_delete=models.CASCADE, related_name='service_capabilities')
    service = models.CharField(max_length=30, choices=ServiceType.choices)
    is_enabled = models.BooleanField(default=False)
    configured_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('workspace', 'service')

    def __str__(self):
        return f"{self.service} - {self.workspace.business.business_name}"
