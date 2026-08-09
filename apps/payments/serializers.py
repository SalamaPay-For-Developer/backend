from rest_framework import serializers
from .models import PaymentCategory, Transaction
from apps.accounts.models import Business

class PaymentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentCategory
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = (
            'reference', 'status', 'selcom_order_id', 'selcom_transid', 
            'payment_token', 'checkout_url', 'completed_at'
        )

class CollectionInitiateSerializer(serializers.Serializer):
    business_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    category_code = serializers.CharField()
    channel = serializers.ChoiceField(choices=Transaction.Channel.choices)
    payer_msisdn = serializers.CharField(max_length=15)

    def validate_business_id(self, value):
        try:
            return Business.objects.get(id=value, is_active=True)
        except Business.DoesNotExist:
            raise serializers.ValidationError("Valid active business required.")

    def validate_category_code(self, value):
        try:
            return PaymentCategory.objects.get(code=value)
        except PaymentCategory.DoesNotExist:
            raise serializers.ValidationError("Valid payment category required.")


class PayoutInitiateSerializer(serializers.Serializer):
    business_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    channel = serializers.ChoiceField(choices=[('mobile', 'Mobile Money'), ('bank', 'Bank Transfer')])

    # Mobile money fields
    recipient_phone = serializers.CharField(max_length=15, required=False, allow_blank=True)

    # Bank transfer fields
    recipient_bank = serializers.CharField(max_length=20, required=False, allow_blank=True)
    recipient_account = serializers.CharField(max_length=50, required=False, allow_blank=True)

    recipient_name = serializers.CharField(max_length=255)
    narration = serializers.CharField(max_length=500, required=False, allow_blank=True)
    webhook_url = serializers.URLField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_amount(self, value):
        if value < 5000:
            raise serializers.ValidationError("amount is below minimum of 5000 TZS for payouts.")
        return value

    def validate_business_id(self, value):
        try:
            return Business.objects.get(id=value, is_active=True)
        except Business.DoesNotExist:
            raise serializers.ValidationError("Valid active business required.")

    def validate(self, attrs):
        if attrs['channel'] == 'mobile' and not attrs.get('recipient_phone'):
            raise serializers.ValidationError({"recipient_phone": "This field is required for mobile payouts."})
        if attrs['channel'] == 'bank' and not (attrs.get('recipient_bank') and attrs.get('recipient_account')):
            raise serializers.ValidationError({"recipient_bank": "recipient_bank and recipient_account are required for bank payouts."})
        return attrs


class PayoutFeeSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("amount must be greater than zero.")
        return value
