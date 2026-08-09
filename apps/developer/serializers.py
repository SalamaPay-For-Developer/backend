from rest_framework import serializers
from .models import (
    DeveloperWorkspace,
    SelcomCredential,
    SalamaPayApiKey,
    WebhookEndpoint,
    WebhookDelivery,
    CheckoutSession,
    ApiLog,
    ServiceCapability,
)


class DeveloperWorkspaceSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source='business.business_name', read_only=True)
    business_type = serializers.CharField(source='business.business_type', read_only=True)
    kyc_status = serializers.CharField(source='business.kyc_status', read_only=True)
    setup_progress = serializers.SerializerMethodField()

    class Meta:
        model = DeveloperWorkspace
        fields = [
            'id', 'business', 'business_name', 'business_type', 'kyc_status',
            'environment', 'production_enabled', 'production_approved_at',
            'selcom_connected', 'webhook_configured', 'test_completed',
            'allowed_domains', 'ip_allowlist', 'setup_progress',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['business', 'production_enabled', 'production_approved_at', 'selcom_connected', 'webhook_configured', 'test_completed']

    def get_setup_progress(self, obj):
        return obj.setup_progress


class ConnectSelcomSerializer(serializers.Serializer):
    environment = serializers.ChoiceField(choices=SelcomCredential.Environment.choices)
    api_key = serializers.CharField(max_length=255)
    api_secret = serializers.CharField(max_length=255)
    vendor_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    pin = serializers.CharField(max_length=255, required=False, allow_blank=True)


class SelcomCredentialSerializer(serializers.ModelSerializer):
    api_key = serializers.SerializerMethodField()
    api_secret = serializers.SerializerMethodField()

    class Meta:
        model = SelcomCredential
        fields = ['id', 'environment', 'api_key', 'api_secret', 'vendor_id', 'is_active', 'last_checked', 'last_check_status']

    def get_api_key(self, obj):
        return obj.masked_api_key

    def get_api_secret(self, obj):
        return obj.masked_api_secret


class SalamaPayApiKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = SalamaPayApiKey
        fields = ['id', 'key_type', 'environment', 'key_prefix', 'is_active', 'last_used', 'created_at']


class CreateApiKeySerializer(serializers.Serializer):
    key_type = serializers.ChoiceField(choices=SalamaPayApiKey.KeyType.choices)
    environment = serializers.ChoiceField(choices=SalamaPayApiKey.Environment.choices)


class WebhookEndpointSerializer(serializers.ModelSerializer):
    delivery_rate = serializers.SerializerMethodField()

    class Meta:
        model = WebhookEndpoint
        fields = [
            'id', 'url', 'description', 'status', 'events', 'secret',
            'total_deliveries', 'successful_deliveries', 'failed_deliveries',
            'delivery_rate', 'created_at', 'updated_at',
        ]
        read_only_fields = ['secret', 'total_deliveries', 'successful_deliveries', 'failed_deliveries']

    def get_delivery_rate(self, obj):
        return obj.delivery_rate


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = [
            'id', 'endpoint', 'event_type', 'payload', 'response_status',
            'response_body', 'status', 'attempt_count', 'delivered_at',
            'error_message', 'transaction_ref', 'created_at',
        ]


class CheckoutSessionSerializer(serializers.ModelSerializer):
    checkout_url = serializers.SerializerMethodField()

    class Meta:
        model = CheckoutSession
        fields = [
            'id', 'order_id', 'amount', 'currency', 'description',
            'customer_name', 'customer_phone', 'customer_email',
            'payment_methods', 'success_url', 'cancel_url',
            'status', 'paid_at', 'checkout_url', 'appearance_config',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['order_id', 'status', 'paid_at', 'selcom_order_id', 'selcom_transid']

    def get_checkout_url(self, obj):
        return obj.checkout_url


class CreateCheckoutSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=10, default='TZS')
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    customer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    payment_methods = serializers.ListField(
        child=serializers.CharField(),
        default=['MOBILE_MONEY', 'CARD', 'BANK']
    )
    success_url = serializers.URLField(required=False, allow_blank=True)
    cancel_url = serializers.URLField(required=False, allow_blank=True)
    appearance_config = serializers.JSONField(required=False, default=dict)


class ApiLogSerializer(serializers.ModelSerializer):
    is_success = serializers.SerializerMethodField()

    class Meta:
        model = ApiLog
        fields = [
            'id', 'method', 'endpoint', 'response_status', 'duration_ms',
            'ip_address', 'user_agent', 'transaction_ref', 'is_success',
            'created_at',
        ]

    def get_is_success(self, obj):
        return obj.is_success


class ApiLogDetailSerializer(serializers.ModelSerializer):
    is_success = serializers.SerializerMethodField()

    class Meta:
        model = ApiLog
        fields = [
            'id', 'method', 'endpoint', 'request_headers', 'request_body',
            'response_status', 'response_body', 'duration_ms',
            'ip_address', 'user_agent', 'transaction_ref', 'is_success',
            'created_at',
        ]

    def get_is_success(self, obj):
        return obj.is_success


class ServiceCapabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCapability
        fields = ['id', 'service', 'is_enabled', 'configured_at']


class DeveloperOverviewSerializer(serializers.Serializer):
    """Aggregate stats for the developer overview dashboard"""
    api_requests_total = serializers.IntegerField()
    api_requests_success = serializers.IntegerField()
    api_requests_failed = serializers.IntegerField()
    transactions_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    transactions_today = serializers.DecimalField(max_digits=12, decimal_places=2)
    webhook_delivery_rate = serializers.FloatField()
    active_checkouts = serializers.IntegerField()
    setup_progress = serializers.DictField()
