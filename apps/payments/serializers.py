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
