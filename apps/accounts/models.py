from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from apps.core.models import BaseModel


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number must be set')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractUser, BaseModel):
    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        ADMIN = 'ADMIN', 'Admin'

    username = None
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True, null=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    is_verified = models.BooleanField(default=False)
    otp_verified = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"


class Business(BaseModel):
    class KYCStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    class BusinessType(models.TextChoices):
        RESTAURANT = 'RESTAURANT', 'Restaurant'
        HOTEL = 'HOTEL', 'Hotel'
        SCHOOL = 'SCHOOL', 'School'
        PHARMACY = 'PHARMACY', 'Pharmacy'
        FUEL_STATION = 'FUEL_STATION', 'Fuel Station'
        TRANSPORT = 'TRANSPORT', 'Transport'
        PROPERTY = 'PROPERTY', 'Property'
        RETAIL_SHOP = 'RETAIL_SHOP', 'Retail Shop'
        MALL = 'MALL', 'Mall / Entertainment'
        GENERAL = 'GENERAL', 'General Business'

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='businesses')
    business_name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=20, choices=BusinessType.choices, default=BusinessType.GENERAL)
    business_category = models.ForeignKey('payments.PaymentCategory', on_delete=models.PROTECT, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    # Legal
    tin = models.CharField(max_length=20, blank=True, null=True)
    brela_number = models.CharField(max_length=30, blank=True, null=True)
    business_license = models.CharField(max_length=50, blank=True, null=True)

    # Selcom
    selcom_vendor_id = models.CharField(max_length=50, blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)
    kyc_status = models.CharField(max_length=20, choices=KYCStatus.choices, default=KYCStatus.PENDING)

    def __str__(self):
        return f"{self.business_name} ({self.business_type})"

    @property
    def is_verified(self):
        return self.kyc_status == self.KYCStatus.APPROVED


class BusinessMember(BaseModel):
    class Role(models.TextChoices):
        OWNER = 'OWNER', 'Owner'
        MANAGER = 'MANAGER', 'Manager'
        CASHIER = 'CASHIER', 'Cashier'
        RECEPTIONIST = 'RECEPTIONIST', 'Receptionist'
        WAITER = 'WAITER', 'Waiter'
        KITCHEN = 'KITCHEN', 'Kitchen Staff'
        ADMINISTRATOR = 'ADMINISTRATOR', 'Administrator'
        ACCOUNTANT = 'ACCOUNTANT', 'Accountant'
        TEACHER = 'TEACHER', 'Teacher'
        STAFF = 'STAFF', 'General Staff'

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_members')

    class Meta:
        unique_together = ('business', 'user')

    def __str__(self):
        return f"{self.user.full_name} - {self.role} @ {self.business.business_name}"


class BusinessKYC(BaseModel):
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name='kyc')

    # Owner Information
    owner_national_id = models.CharField(max_length=20, blank=True, null=True)
    owner_address = models.TextField(blank=True, null=True)
    owner_phone = models.CharField(max_length=15, blank=True, null=True)
    selfie_verified = models.BooleanField(default=False)

    # Bank / Settlement
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_number = models.CharField(max_length=30, blank=True, null=True)
    bank_account_name = models.CharField(max_length=100, blank=True, null=True)

    # Review
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='kyc_reviews')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"KYC for {self.business.business_name}"


class KYCDocument(BaseModel):
    class DocumentType(models.TextChoices):
        BUSINESS_LICENSE = 'BUSINESS_LICENSE', 'Business License'
        CERTIFICATE = 'CERTIFICATE', 'Certificate'
        OWNER_ID = 'OWNER_ID', 'Owner National ID'
        SELFIE = 'SELFIE', 'Selfie Verification'
        OTHER = 'OTHER', 'Other Supporting Document'

    kyc = models.ForeignKey(BusinessKYC, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file = models.FileField(upload_to='kyc_documents/', null=True, blank=True)
    file_url = models.URLField(max_length=500, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.document_type} - {self.kyc.business.business_name}"
