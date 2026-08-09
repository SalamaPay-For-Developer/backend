from rest_framework import serializers
from .models import (
    Permission, Role, Department, Branch, StaffProfile, AuditLog,
    BusinessTypeConfig, FeeConfig, FeeTier, SettlementFee, CommissionRule,
    Biller, PaymentService, SalesLead, SupportTicket, TicketComment,
    Refund, SystemNotification, SystemSetting,
)
from apps.accounts.models import User, Business, BusinessKYC
from apps.payments.models import Transaction


# ==================== RBAC Serializers ====================

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'code', 'name', 'module', 'description']


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_codes = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'is_builtin', 'is_active', 'permissions', 'permission_codes', 'staff_count', 'created_at']

    def get_staff_count(self, obj):
        return obj.staff_members.count()

    def create(self, validated_data):
        perm_codes = validated_data.pop('permission_codes', [])
        role = Role.objects.create(**validated_data)
        if perm_codes:
            perms = Permission.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
        return role

    def update(self, instance, validated_data):
        perm_codes = validated_data.pop('permission_codes', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if perm_codes is not None:
            perms = Permission.objects.filter(code__in=perm_codes)
            instance.permissions.set(perms)
        return instance


class DepartmentSerializer(serializers.ModelSerializer):
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'is_active', 'staff_count', 'created_at']

    def get_staff_count(self, obj):
        return obj.staff.count()


class BranchSerializer(serializers.ModelSerializer):
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = ['id', 'name', 'address', 'phone', 'is_active', 'staff_count', 'created_at']

    def get_staff_count(self, obj):
        return obj.staff.count()


class StaffProfileSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    effective_permissions = serializers.SerializerMethodField()

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'user', 'user_phone', 'user_name', 'user_email',
            'role', 'role_name', 'department', 'department_name',
            'branch', 'branch_name', 'status', 'can_access_all_branches',
            'employee_id', 'hired_at', 'invited_by',
            'effective_permissions', 'created_at',
        ]
        read_only_fields = ['user', 'invited_by']


class CreateStaffSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True)
    role = serializers.CharField()
    department = serializers.CharField(required=False, allow_blank=True)
    branch = serializers.CharField(required=False, allow_blank=True)
    can_access_all_branches = serializers.BooleanField(default=False)
    employee_id = serializers.CharField(max_length=50, required=False, allow_blank=True)


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.full_name', read_only=True, default='System')

    class Meta:
        model = AuditLog
        fields = [
            'id', 'actor', 'actor_name', 'action', 'module', 'target_type',
            'target_id', 'description', 'old_values', 'new_values',
            'ip_address', 'user_agent', 'created_at',
        ]


# ==================== Admin User Management ====================

class AdminUserSerializer(serializers.ModelSerializer):
    businesses_count = serializers.SerializerMethodField()
    transactions_count = serializers.SerializerMethodField()
    has_staff_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'email', 'full_name', 'role', 'is_verified',
            'otp_verified', 'is_active', 'has_staff_profile',
            'businesses_count', 'transactions_count', 'created_at',
        ]

    def get_businesses_count(self, obj):
        return obj.businesses.count()

    def get_transactions_count(self, obj):
        return obj.transactions.count()

    def get_has_staff_profile(self, obj):
        return hasattr(obj, 'staff_profile')


class AdminUserDetailSerializer(AdminUserSerializer):
    staff_profile = StaffProfileSerializer(read_only=True)

    class Meta(AdminUserSerializer.Meta):
        fields = AdminUserSerializer.Meta.fields + ['staff_profile']


# ==================== Admin Business Management ====================

class AdminBusinessSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    owner_phone = serializers.CharField(source='owner.phone_number', read_only=True)
    transactions_count = serializers.SerializerMethodField()
    kyc_status_display = serializers.CharField(source='get_kyc_status_display', read_only=True)

    class Meta:
        model = Business
        fields = [
            'id', 'business_name', 'business_type', 'owner_name', 'owner_phone',
            'kyc_status', 'kyc_status_display', 'is_active', 'selcom_vendor_id',
            'tin', 'brela_number', 'business_license', 'description',
            'transactions_count', 'created_at',
        ]

    def get_transactions_count(self, obj):
        return obj.transactions.count()


class AdminBusinessDetailSerializer(AdminBusinessSerializer):
    kyc = serializers.SerializerMethodField()

    class Meta(AdminBusinessSerializer.Meta):
        fields = AdminBusinessSerializer.Meta.fields + ['kyc']

    def get_kyc(self, obj):
        try:
            kyc = obj.kyc
            return {
                'owner_national_id': kyc.owner_national_id,
                'owner_address': kyc.owner_address,
                'owner_phone': kyc.owner_phone,
                'selfie_verified': kyc.selfie_verified,
                'bank_name': kyc.bank_name,
                'bank_account_number': kyc.bank_account_number,
                'bank_account_name': kyc.bank_account_name,
                'reviewed_at': kyc.reviewed_at,
                'rejection_reason': kyc.rejection_reason,
            }
        except BusinessKYC.DoesNotExist:
            return None


# ==================== Business Type Config ====================

class BusinessTypeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessTypeConfig
        fields = [
            'id', 'name', 'code', 'is_active', 'icon',
            'requires_tin', 'requires_brela', 'requires_license',
            'requires_national_id', 'requires_bank_account', 'requires_selfie',
            'required_documents', 'default_fee_percentage',
        ]


# ==================== Fee Management ====================

class FeeTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeTier
        fields = ['id', 'fee_config', 'min_amount', 'max_amount', 'percentage', 'fixed_fee']


class FeeConfigSerializer(serializers.ModelSerializer):
    tiers = FeeTierSerializer(many=True, read_only=True)
    business_type_name = serializers.CharField(source='business_type.name', read_only=True, default=None)

    class Meta:
        model = FeeConfig
        fields = [
            'id', 'name', 'channel', 'fee_type', 'percentage', 'fixed_fee',
            'min_fee', 'max_fee', 'business_type', 'business_type_name',
            'is_active', 'tiers', 'created_at',
        ]


class SettlementFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SettlementFee
        fields = ['id', 'name', 'fee_type', 'fixed_fee', 'percentage', 'is_active', 'created_at']


class CommissionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionRule
        fields = ['id', 'name', 'commission_type', 'calculation_type', 'percentage', 'fixed_amount', 'is_active', 'created_at']


# ==================== Billers ====================

class BillerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Biller
        fields = ['id', 'name', 'code', 'category', 'utility_code', 'is_active', 'description', 'logo_url', 'created_at']


# ==================== Payment Services ====================

class PaymentServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentService
        fields = ['id', 'name', 'code', 'status', 'description', 'icon', 'created_at']


# ==================== Sales CRM ====================

class SalesLeadSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True, default=None)
    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)

    class Meta:
        model = SalesLead
        fields = [
            'id', 'business_name', 'contact_name', 'contact_phone', 'contact_email',
            'business_type', 'stage', 'priority', 'assigned_to', 'assigned_to_name',
            'branch', 'branch_name', 'notes', 'follow_up_date',
            'converted_business', 'created_at',
        ]


# ==================== Support Tickets ====================

class TicketCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True, default='System')

    class Meta:
        model = TicketComment
        fields = ['id', 'ticket', 'author', 'author_name', 'comment', 'is_internal', 'created_at']


class SupportTicketSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True, default=None)
    business_name = serializers.CharField(source='business.business_name', read_only=True, default=None)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True, default=None)
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    comments = TicketCommentSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_number', 'subject', 'description', 'category', 'priority', 'status',
            'user', 'user_name', 'business', 'business_name', 'transaction',
            'assigned_to', 'assigned_to_name', 'department', 'department_name', 'branch',
            'resolved_at', 'resolution_notes', 'comments', 'created_at',
        ]


# ==================== Refunds ====================

class RefundSerializer(serializers.ModelSerializer):
    transaction_ref = serializers.CharField(source='transaction.reference', read_only=True)
    transaction_amount = serializers.DecimalField(source='transaction.amount', max_digits=14, decimal_places=2, read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.full_name', read_only=True, default=None)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True, default=None)
    business_name = serializers.SerializerMethodField()

    class Meta:
        model = Refund
        fields = [
            'id', 'transaction', 'transaction_ref', 'transaction_amount',
            'amount', 'reason', 'status', 'requested_by', 'requested_by_name',
            'approved_by', 'approved_by_name', 'requested_at', 'approved_at',
            'completed_at', 'rejection_reason', 'business_name', 'created_at',
        ]

    def get_business_name(self, obj):
        if obj.transaction.business:
            return obj.transaction.business.business_name
        return None


# ==================== Notifications ====================

class SystemNotificationSerializer(serializers.ModelSerializer):
    sent_by_name = serializers.CharField(source='sent_by.full_name', read_only=True, default=None)

    class Meta:
        model = SystemNotification
        fields = ['id', 'title', 'message', 'channel', 'target_type', 'sent_by', 'sent_by_name', 'sent_at', 'created_at']


# ==================== System Settings ====================

class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ['id', 'key', 'value', 'description', 'is_public', 'created_at', 'updated_at']


# ==================== Admin Transaction Serializer ====================

class AdminTransactionSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source='business.business_name', read_only=True, default=None)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True, default=None)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True, default=None)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'reference', 'business', 'business_name', 'customer_name', 'customer_phone',
            'type', 'amount', 'currency', 'channel', 'channel_display',
            'status', 'status_display', 'selcom_transid', 'payer_msisdn',
            'failure_reason', 'completed_at', 'created_at',
        ]


# ==================== Admin Overview ====================

class AdminOverviewSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    new_registrations = serializers.IntegerField()
    total_businesses = serializers.IntegerField()
    pending_kyc = serializers.IntegerField()
    verified_businesses = serializers.IntegerField()
    suspended_businesses = serializers.IntegerField()
    total_transactions = serializers.IntegerField()
    successful_transactions = serializers.IntegerField()
    failed_transactions = serializers.IntegerField()
    pending_transactions = serializers.IntegerField()
    total_payment_volume = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_fees = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_settlements = serializers.IntegerField()
    today_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    monthly_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    active_developers = serializers.IntegerField()
    api_requests = serializers.IntegerField()
    failed_api_requests = serializers.IntegerField()
    open_tickets = serializers.IntegerField()
