from rest_framework import serializers
from .models import User, Business, BusinessMember, BusinessKYC, KYCDocument
from apps.wallets.models import Wallet


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'phone_number', 'full_name', 'email', 'role', 'is_verified', 'otp_verified', 'password')
        read_only_fields = ('id', 'is_verified', 'otp_verified', 'role')

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        Wallet.objects.create(owner=user, wallet_type=Wallet.WalletType.PERSONAL)
        return user


class BusinessMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model = BusinessMember
        fields = '__all__'
        read_only_fields = ('business', 'invited_by')


class BusinessSerializer(serializers.ModelSerializer):
    members = BusinessMemberSerializer(many=True, read_only=True)
    module_name = serializers.CharField(source='module_config.module.name', read_only=True, default=None)

    class Meta:
        model = Business
        fields = '__all__'
        read_only_fields = ('owner', 'kyc_status', 'selcom_vendor_id', 'is_active')

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        business = super().create(validated_data)
        BusinessMember.objects.create(
            business=business,
            user=self.context['request'].user,
            role=BusinessMember.Role.OWNER,
        )
        Wallet.objects.create(business=business, wallet_type=Wallet.WalletType.BUSINESS)
        return business


class BusinessKYCSerializer(serializers.ModelSerializer):
    documents = serializers.SerializerMethodField()

    class Meta:
        model = BusinessKYC
        fields = '__all__'
        read_only_fields = ('reviewed_by', 'reviewed_at', 'rejection_reason')

    def get_documents(self, obj):
        docs = obj.documents.all()
        return KYCDocumentSerializer(docs, many=True).data


class KYCDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCDocument
        fields = '__all__'
        read_only_fields = ('is_verified',)
