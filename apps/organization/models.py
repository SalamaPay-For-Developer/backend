from django.db import models
from django.conf import settings
from apps.core.models import BaseModel


# ==================== RBAC Core ====================

class Permission(BaseModel):
    """Granular permission entity. e.g. users.view, fees.update, refunds.approve"""
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    module = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['module', 'code']

    def __str__(self):
        return f"{self.code} ({self.name})"


class Role(BaseModel):
    """Staff role: Super Admin, Admin, KYC Officer, Finance, Sales, Call Center, etc."""
    class Builtin(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        ADMIN = 'ADMIN', 'Admin'
        OPERATIONS_MANAGER = 'OPERATIONS_MANAGER', 'Operations Manager'
        KYC_OFFICER = 'KYC_OFFICER', 'KYC Officer'
        FINANCE = 'FINANCE', 'Finance'
        SALES = 'SALES', 'Sales'
        CALL_CENTER = 'CALL_CENTER', 'Call Center'
        RECEPTION = 'RECEPTION', 'Reception'
        TECHNICAL_SUPPORT = 'TECHNICAL_SUPPORT', 'Technical Support'

    name = models.CharField(max_length=100, unique=True)
    is_builtin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name='roles')

    def __str__(self):
        return self.name


class Department(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Branch(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class StaffProfile(BaseModel):
    """Links a User to staff-specific data: role, department, branch, permissions."""
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        INVITED = 'INVITED', 'Invited'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='staff_members')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INVITED)

    # Extra granular permissions on top of role permissions
    extra_permissions = models.ManyToManyField(Permission, blank=True, related_name='granted_staff')
    revoked_permissions = models.ManyToManyField(Permission, blank=True, related_name='revoked_staff')

    # Scope
    can_access_all_branches = models.BooleanField(default=False)

    # Metadata
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    hired_at = models.DateField(null=True, blank=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_staff')

    def __str__(self):
        return f"{self.user.full_name} - {self.role.name}"

    @property
    def effective_permissions(self):
        """Return the set of permission codes this staff member has."""
        role_perms = set(self.role.permissions.values_list('code', flat=True))
        extra_perms = set(self.extra_permissions.values_list('code', flat=True))
        revoked_perms = set(self.revoked_permissions.values_list('code', flat=True))
        return (role_perms | extra_perms) - revoked_perms

    def has_permission(self, perm_code):
        return perm_code in self.effective_permissions


class AuditLog(BaseModel):
    """Tracks every critical action in the system."""
    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        APPROVE = 'APPROVE', 'Approve'
        REJECT = 'REJECT', 'Reject'
        SUSPEND = 'SUSPEND', 'Suspend'
        ACTIVATE = 'ACTIVATE', 'Activate'
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        EXPORT = 'EXPORT', 'Export'
        OTHER = 'OTHER', 'Other'

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_actions')
    action = models.CharField(max_length=20, choices=Action.choices)
    module = models.CharField(max_length=50)
    target_type = models.CharField(max_length=100, blank=True, null=True)
    target_id = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.actor} - {self.action} - {self.module} - {self.created_at}"


# ==================== Business Type Management ====================

class BusinessTypeConfig(BaseModel):
    """Dynamic business type configuration managed by admin."""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, blank=True, null=True)

    # KYC requirements
    requires_tin = models.BooleanField(default=True)
    requires_brela = models.BooleanField(default=False)
    requires_license = models.BooleanField(default=True)
    requires_national_id = models.BooleanField(default=True)
    requires_bank_account = models.BooleanField(default=True)
    requires_selfie = models.BooleanField(default=False)

    # Required documents
    required_documents = models.JSONField(default=list, blank=True)

    # Default fee percentage for this business type
    default_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=1.5)

    def __str__(self):
        return self.name


# ==================== Fee Management ====================

class FeeConfig(BaseModel):
    class FeeType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentage'
        FIXED = 'FIXED', 'Fixed'
        TIERED = 'TIERED', 'Tiered'

    class Channel(models.TextChoices):
        MOBILE_MONEY = 'MOBILE_MONEY', 'Mobile Money'
        CARD = 'CARD', 'Card'
        BANK = 'BANK', 'Bank'
        QR = 'QR', 'QR'
        UTILITY = 'UTILITY', 'Utility'
        GOVERNMENT = 'GOVERNMENT', 'Government'

    name = models.CharField(max_length=100)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    fee_type = models.CharField(max_length=20, choices=FeeType.choices, default=FeeType.PERCENTAGE)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    fixed_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    min_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    max_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Optional: link to business type for type-specific fees
    business_type = models.ForeignKey(BusinessTypeConfig, on_delete=models.CASCADE, null=True, blank=True, related_name='fees')

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['channel', 'name']

    def __str__(self):
        return f"{self.name} - {self.channel}"


class FeeTier(BaseModel):
    """Tiered fee structure: e.g. <50k = 1.5%, 50k-500k = 1.2%, >500k = 1%"""
    fee_config = models.ForeignKey(FeeConfig, on_delete=models.CASCADE, related_name='tiers')
    min_amount = models.DecimalField(max_digits=14, decimal_places=2)
    max_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    fixed_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)

    class Meta:
        ordering = ['min_amount']

    def __str__(self):
        return f"{self.fee_config.name} - {self.min_amount} to {self.max_amount or 'inf'}"


class SettlementFee(BaseModel):
    class FeeType(models.TextChoices):
        FIXED = 'FIXED', 'Fixed'
        PERCENTAGE = 'PERCENTAGE', 'Percentage'
        TIERED = 'TIERED', 'Tiered'

    name = models.CharField(max_length=100)
    fee_type = models.CharField(max_length=20, choices=FeeType.choices, default=FeeType.FIXED)
    fixed_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Settlement Fee - {self.name}"


# ==================== Commission Management ====================

class CommissionRule(BaseModel):
    class CommissionType(models.TextChoices):
        SALES_AGENT = 'SALES_AGENT', 'Sales Agent'
        PARTNER = 'PARTNER', 'Partner'
        REFERRAL = 'REFERRAL', 'Referral'
        AFFILIATE = 'AFFILIATE', 'Affiliate'

    class CalculationType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentage'
        FIXED = 'FIXED', 'Fixed'

    name = models.CharField(max_length=100)
    commission_type = models.CharField(max_length=20, choices=CommissionType.choices)
    calculation_type = models.CharField(max_length=20, choices=CalculationType.choices, default=CalculationType.PERCENTAGE)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.commission_type}"


# ==================== Billers ====================

class Biller(BaseModel):
    class Category(models.TextChoices):
        ELECTRICITY = 'ELECTRICITY', 'Electricity'
        WATER = 'WATER', 'Water'
        TV = 'TV', 'TV / DTH'
        INTERNET = 'INTERNET', 'Internet'
        GOVERNMENT = 'GOVERNMENT', 'Government'
        TELECOM = 'TELECOM', 'Telecom'
        OTHER = 'OTHER', 'Other'

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    utility_code = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    logo_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


# ==================== Payment Services ====================

class PaymentService(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'
        RESTRICTED = 'RESTRICTED', 'Restricted'

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.status})"


# ==================== Sales CRM ====================

class SalesLead(BaseModel):
    class Stage(models.TextChoices):
        LEAD = 'LEAD', 'Lead'
        CONTACTED = 'CONTACTED', 'Contacted'
        INTERESTED = 'INTERESTED', 'Interested'
        KYC_STARTED = 'KYC_STARTED', 'KYC Started'
        KYC_SUBMITTED = 'KYC_SUBMITTED', 'KYC Submitted'
        APPROVED = 'APPROVED', 'Approved'
        ACTIVATED = 'ACTIVATED', 'Activated'
        LOST = 'LOST', 'Lost'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'

    business_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    business_type = models.CharField(max_length=50, blank=True, null=True)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.LEAD)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)

    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')

    notes = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(null=True, blank=True)
    converted_business = models.ForeignKey('accounts.Business', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_lead')

    def __str__(self):
        return f"{self.business_name} - {self.stage}"


# ==================== Support Tickets ====================

class SupportTicket(BaseModel):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    class Category(models.TextChoices):
        PAYMENT = 'PAYMENT', 'Payment'
        ACCOUNT = 'ACCOUNT', 'Account'
        KYC = 'KYC', 'KYC'
        SETTLEMENT = 'SETTLEMENT', 'Settlement'
        TECHNICAL = 'TECHNICAL', 'Technical'
        REFUND = 'REFUND', 'Refund'
        BUSINESS = 'BUSINESS', 'Business'
        OTHER = 'OTHER', 'Other'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    ticket_number = models.CharField(max_length=50, unique=True)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    # Related entities
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    business = models.ForeignKey('accounts.Business', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    transaction = models.ForeignKey('payments.Transaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')

    # Assignment
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')

    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.ticket_number} - {self.subject}"


class TicketComment(BaseModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='ticket_comments')
    comment = models.TextField()
    is_internal = models.BooleanField(default=False)

    def __str__(self):
        return f"Comment on {self.ticket.ticket_number}"


# ==================== Refunds ====================

class Refund(BaseModel):
    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', 'Requested'
        APPROVED = 'APPROVED', 'Approved'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        REJECTED = 'REJECTED', 'Rejected'

    transaction = models.ForeignKey('payments.Transaction', on_delete=models.PROTECT, related_name='refunds')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='requested_refunds')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_refunds')

    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Refund - {self.transaction.reference} - {self.amount} - {self.status}"


# ==================== Notifications ====================

class SystemNotification(BaseModel):
    class Channel(models.TextChoices):
        SYSTEM = 'SYSTEM', 'System'
        SMS = 'SMS', 'SMS'
        EMAIL = 'EMAIL', 'Email'
        PUSH = 'PUSH', 'Push'

    class TargetType(models.TextChoices):
        ALL = 'ALL', 'All Users'
        BUSINESSES = 'BUSINESSES', 'Businesses'
        DEVELOPERS = 'DEVELOPERS', 'Developers'
        STAFF = 'STAFF', 'Staff'
        SPECIFIC = 'SPECIFIC', 'Specific Users'

    title = models.CharField(max_length=255)
    message = models.TextField()
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.SYSTEM)
    target_type = models.CharField(max_length=20, choices=TargetType.choices, default=TargetType.ALL)

    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sent_notifications')
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.channel})"


# ==================== System Settings ====================

class SystemSetting(BaseModel):
    """Key-value system configuration."""
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.key}"
