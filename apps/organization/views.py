import csv
from datetime import timedelta
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import User, Business, BusinessKYC
from apps.payments.models import Transaction
from apps.developer.models import DeveloperWorkspace, ApiLog

from .models import (
    Permission, Role, Department, Branch, StaffProfile, AuditLog,
    BusinessTypeConfig, FeeConfig, FeeTier, SettlementFee, CommissionRule,
    Biller, PaymentService, SalesLead, SupportTicket, TicketComment,
    Refund, SystemNotification, SystemSetting,
)
from .serializers import (
    PermissionSerializer, RoleSerializer, DepartmentSerializer, BranchSerializer,
    StaffProfileSerializer, CreateStaffSerializer, AuditLogSerializer,
    AdminUserSerializer, AdminUserDetailSerializer,
    AdminBusinessSerializer, AdminBusinessDetailSerializer,
    BusinessTypeConfigSerializer, FeeConfigSerializer, FeeTierSerializer,
    SettlementFeeSerializer, CommissionRuleSerializer,
    BillerSerializer, PaymentServiceSerializer,
    SalesLeadSerializer, SupportTicketSerializer, TicketCommentSerializer,
    RefundSerializer, SystemNotificationSerializer, SystemSettingSerializer,
    AdminTransactionSerializer,
)
from .permissions import IsStaff, PermissionRequiredMixin, require_permission, log_audit


# ==================== Admin Overview ====================

class AdminOverviewView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        users = User.objects.all()
        businesses = Business.objects.all()
        txns = Transaction.objects.all()
        tickets = SupportTicket.objects.all()

        successful = txns.filter(status=Transaction.Status.SUCCESS)
        today_revenue = successful.filter(completed_at__gte=today_start).aggregate(
            total=Sum('amount'))['total'] or 0
        monthly_revenue = successful.filter(completed_at__gte=month_start).aggregate(
            total=Sum('amount'))['total'] or 0

        api_logs = ApiLog.objects.all()

        return Response({
            'total_users': users.count(),
            'active_users': users.filter(is_active=True).count(),
            'new_registrations': users.filter(created_at__gte=today_start).count(),
            'total_businesses': businesses.count(),
            'pending_kyc': businesses.filter(kyc_status=Business.KYCStatus.PENDING).count(),
            'verified_businesses': businesses.filter(kyc_status=Business.KYCStatus.APPROVED).count(),
            'suspended_businesses': businesses.filter(is_active=False).count(),
            'total_transactions': txns.count(),
            'successful_transactions': successful.count(),
            'failed_transactions': txns.filter(status=Transaction.Status.FAILED).count(),
            'pending_transactions': txns.filter(status__in=[Transaction.Status.PENDING, Transaction.Status.PROCESSING]).count(),
            'total_payment_volume': successful.aggregate(total=Sum('amount'))['total'] or 0,
            'total_fees': 0,
            'total_settlements': 0,
            'today_revenue': today_revenue,
            'monthly_revenue': monthly_revenue,
            'active_developers': DeveloperWorkspace.objects.filter(selcom_connected=True).count(),
            'api_requests': api_logs.count(),
            'failed_api_requests': api_logs.filter(response_status__gte=400).count(),
            'open_tickets': tickets.filter(status__in=[SupportTicket.Status.OPEN, SupportTicket.Status.PENDING, SupportTicket.Status.IN_PROGRESS]).count(),
        })


# ==================== User Management ====================

class AdminUserViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AdminUserDetailSerializer
        return AdminUserSerializer

    required_permissions = {
        'list': 'users.view',
        'retrieve': 'users.view',
        'create': 'users.create',
        'update': 'users.update',
        'partial_update': 'users.update',
        'destroy': 'users.delete',
    }

    def get_queryset(self):
        qs = User.objects.all().order_by('-created_at')
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(email__icontains=search)
            )
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        return qs

    @action(detail=True, methods=['post'])
    @require_permission('users.suspend')
    def suspend(self, request, pk=None):
        user = self.get_object()
        old = {'is_active': user.is_active}
        user.is_active = False
        user.save(update_fields=['is_active'])
        log_audit(request.user, 'SUSPEND', 'users', f'Suspended user {user.phone_number}',
                  target_type='User', target_id=user.id, old_values=old,
                  new_values={'is_active': False}, request=request)
        return Response({'detail': 'User suspended.'})

    @action(detail=True, methods=['post'])
    @require_permission('users.activate')
    def activate(self, request, pk=None):
        user = self.get_object()
        old = {'is_active': user.is_active}
        user.is_active = True
        user.save(update_fields=['is_active'])
        log_audit(request.user, 'ACTIVATE', 'users', f'Activated user {user.phone_number}',
                  target_type='User', target_id=user.id, old_values=old,
                  new_values={'is_active': True}, request=request)
        return Response({'detail': 'User activated.'})

    @action(detail=True, methods=['post'])
    @require_permission('users.verify')
    def verify_phone(self, request, pk=None):
        user = self.get_object()
        user.is_verified = True
        user.otp_verified = True
        user.save(update_fields=['is_verified', 'otp_verified'])
        log_audit(request.user, 'UPDATE', 'users', f'Verified phone for {user.phone_number}',
                  target_type='User', target_id=user.id, request=request)
        return Response({'detail': 'Phone verified.'})

    @action(detail=True, methods=['get'])
    @require_permission('users.view')
    def transactions(self, request, pk=None):
        user = self.get_object()
        txns = Transaction.objects.filter(customer=user).order_by('-created_at')[:50]
        return Response(AdminTransactionSerializer(txns, many=True).data)

    @action(detail=True, methods=['get'])
    @require_permission('users.view')
    def businesses(self, request, pk=None):
        user = self.get_object()
        businesses = Business.objects.filter(owner=user)
        return Response(AdminBusinessSerializer(businesses, many=True).data)


# ==================== Business Management ====================

class AdminBusinessViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = Business.objects.all().order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AdminBusinessDetailSerializer
        return AdminBusinessSerializer

    required_permissions = {
        'list': 'businesses.view',
        'retrieve': 'businesses.view',
        'update': 'businesses.update',
        'partial_update': 'businesses.update',
    }

    def get_queryset(self):
        qs = Business.objects.all().order_by('-created_at')
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(business_name__icontains=search) |
                Q(owner__full_name__icontains=search) |
                Q(owner__phone_number__icontains=search)
            )
        kyc_status = self.request.query_params.get('kyc_status')
        if kyc_status:
            qs = qs.filter(kyc_status=kyc_status)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        return qs

    @action(detail=True, methods=['post'])
    @require_permission('businesses.approve')
    def approve_kyc(self, request, pk=None):
        business = self.get_object()
        old = {'kyc_status': business.kyc_status}
        business.kyc_status = Business.KYCStatus.APPROVED
        business.save(update_fields=['kyc_status'])
        log_audit(request.user, 'APPROVE', 'businesses', f'Approved KYC for {business.business_name}',
                  target_type='Business', target_id=business.id, old_values=old,
                  new_values={'kyc_status': 'APPROVED'}, request=request)
        return Response({'detail': 'Business KYC approved.'})

    @action(detail=True, methods=['post'])
    @require_permission('businesses.reject')
    def reject_kyc(self, request, pk=None):
        business = self.get_object()
        reason = request.data.get('reason', '')
        old = {'kyc_status': business.kyc_status}
        business.kyc_status = Business.KYCStatus.REJECTED
        business.save(update_fields=['kyc_status'])
        try:
            kyc = business.kyc
            kyc.rejection_reason = reason
            kyc.save(update_fields=['rejection_reason'])
        except BusinessKYC.DoesNotExist:
            pass
        log_audit(request.user, 'REJECT', 'businesses', f'Rejected KYC for {business.business_name}: {reason}',
                  target_type='Business', target_id=business.id, old_values=old,
                  new_values={'kyc_status': 'REJECTED'}, request=request)
        return Response({'detail': 'Business KYC rejected.'})

    @action(detail=True, methods=['post'])
    @require_permission('businesses.suspend')
    def suspend(self, request, pk=None):
        business = self.get_object()
        old = {'is_active': business.is_active}
        business.is_active = False
        business.save(update_fields=['is_active'])
        log_audit(request.user, 'SUSPEND', 'businesses', f'Suspended {business.business_name}',
                  target_type='Business', target_id=business.id, old_values=old,
                  new_values={'is_active': False}, request=request)
        return Response({'detail': 'Business suspended.'})

    @action(detail=True, methods=['post'])
    @require_permission('businesses.activate')
    def reactivate(self, request, pk=None):
        business = self.get_object()
        old = {'is_active': business.is_active}
        business.is_active = True
        business.save(update_fields=['is_active'])
        log_audit(request.user, 'ACTIVATE', 'businesses', f'Reactivated {business.business_name}',
                  target_type='Business', target_id=business.id, old_values=old,
                  new_values={'is_active': True}, request=request)
        return Response({'detail': 'Business reactivated.'})

    @action(detail=True, methods=['get'])
    @require_permission('businesses.view')
    def transactions(self, request, pk=None):
        business = self.get_object()
        txns = Transaction.objects.filter(business=business).order_by('-created_at')[:50]
        return Response(AdminTransactionSerializer(txns, many=True).data)


# ==================== RBAC: Permissions ====================

class PermissionViewSet(PermissionRequiredMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.all().order_by('module', 'code')
    serializer_class = PermissionSerializer
    required_permissions = {'list': 'permissions.view', 'retrieve': 'permissions.view'}


# ==================== RBAC: Roles ====================

class RoleViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = Role.objects.all().order_by('name')
    serializer_class = RoleSerializer
    required_permissions = {
        'list': 'roles.view',
        'retrieve': 'roles.view',
        'create': 'roles.create',
        'update': 'roles.update',
        'partial_update': 'roles.update',
        'destroy': 'roles.delete',
    }


# ==================== RBAC: Departments ====================

class DepartmentViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by('name')
    serializer_class = DepartmentSerializer
    required_permissions = {
        'list': 'departments.view',
        'retrieve': 'departments.view',
        'create': 'departments.create',
        'update': 'departments.update',
        'partial_update': 'departments.update',
        'destroy': 'departments.delete',
    }


# ==================== RBAC: Branches ====================

class BranchViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = Branch.objects.all().order_by('name')
    serializer_class = BranchSerializer
    required_permissions = {
        'list': 'branches.view',
        'retrieve': 'branches.view',
        'create': 'branches.create',
        'update': 'branches.update',
        'partial_update': 'branches.update',
        'destroy': 'branches.delete',
    }


# ==================== Staff Management ====================

class StaffViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = StaffProfile.objects.select_related('user', 'role', 'department', 'branch').all().order_by('-created_at')
    serializer_class = StaffProfileSerializer
    required_permissions = {
        'list': 'staff.view',
        'retrieve': 'staff.view',
        'update': 'staff.update',
        'partial_update': 'staff.update',
        'destroy': 'staff.delete',
    }

    def create(self, request, *args, **kwargs):
        serializer = CreateStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Create or find user
        user, created = User.objects.get_or_create(
            phone_number=data['phone_number'],
            defaults={'full_name': data['full_name'], 'email': data.get('email', '')}
        )
        if not created:
            if hasattr(user, 'staff_profile'):
                return Response({'detail': 'User already has a staff profile.'}, status=status.HTTP_400_BAD_REQUEST)

        role = get_object_or_404(Role, id=data['role'])
        department = Department.objects.filter(id=data['department']).first() if data.get('department') else None
        branch = Branch.objects.filter(id=data['branch']).first() if data.get('branch') else None

        profile = StaffProfile.objects.create(
            user=user,
            role=role,
            department=department,
            branch=branch,
            status=StaffProfile.Status.INVITED,
            can_access_all_branches=data.get('can_access_all_branches', False),
            employee_id=data.get('employee_id'),
            invited_by=request.user,
        )
        log_audit(request.user, 'CREATE', 'staff', f'Created staff {user.full_name}',
                  target_type='StaffProfile', target_id=profile.id, request=request)
        return Response(StaffProfileSerializer(profile).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    @require_permission('staff.suspend')
    def suspend(self, request, pk=None):
        profile = self.get_object()
        profile.status = StaffProfile.Status.SUSPENDED
        profile.save(update_fields=['status'])
        log_audit(request.user, 'SUSPEND', 'staff', f'Suspended staff {profile.user.full_name}',
                  target_type='StaffProfile', target_id=profile.id, request=request)
        return Response({'detail': 'Staff suspended.'})

    @action(detail=True, methods=['post'])
    @require_permission('staff.activate')
    def activate(self, request, pk=None):
        profile = self.get_object()
        profile.status = StaffProfile.Status.ACTIVE
        profile.save(update_fields=['status'])
        log_audit(request.user, 'ACTIVATE', 'staff', f'Activated staff {profile.user.full_name}',
                  target_type='StaffProfile', target_id=profile.id, request=request)
        return Response({'detail': 'Staff activated.'})


# ==================== Audit Logs ====================

class AuditLogViewSet(PermissionRequiredMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().order_by('-created_at')
    serializer_class = AuditLogSerializer
    required_permissions = {'list': 'audit_logs.view', 'retrieve': 'audit_logs.view'}

    def get_queryset(self):
        qs = AuditLog.objects.all().order_by('-created_at')
        module = self.request.query_params.get('module')
        if module:
            qs = qs.filter(module=module)
        action = self.request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)
        return qs[:500]  # Limit to last 500


# ==================== Business Type Config ====================

class BusinessTypeConfigViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = BusinessTypeConfig.objects.all().order_by('name')
    serializer_class = BusinessTypeConfigSerializer
    required_permissions = {
        'list': 'business_types.view',
        'retrieve': 'business_types.view',
        'create': 'business_types.create',
        'update': 'business_types.update',
        'partial_update': 'business_types.update',
        'destroy': 'business_types.delete',
    }


# ==================== Fee Management ====================

class FeeConfigViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = FeeConfig.objects.all().order_by('-created_at')
    serializer_class = FeeConfigSerializer
    required_permissions = {
        'list': 'fees.view',
        'retrieve': 'fees.view',
        'create': 'fees.update',
        'update': 'fees.update',
        'partial_update': 'fees.update',
        'destroy': 'fees.update',
    }


class SettlementFeeViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = SettlementFee.objects.all().order_by('-created_at')
    serializer_class = SettlementFeeSerializer
    required_permissions = {
        'list': 'fees.view',
        'retrieve': 'fees.view',
        'create': 'fees.update',
        'update': 'fees.update',
        'partial_update': 'fees.update',
        'destroy': 'fees.update',
    }


class CommissionRuleViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = CommissionRule.objects.all().order_by('-created_at')
    serializer_class = CommissionRuleSerializer
    required_permissions = {
        'list': 'commissions.view',
        'retrieve': 'commissions.view',
        'create': 'commissions.update',
        'update': 'commissions.update',
        'partial_update': 'commissions.update',
        'destroy': 'commissions.update',
    }


# ==================== Billers ====================

class BillerViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = Biller.objects.all().order_by('name')
    serializer_class = BillerSerializer
    required_permissions = {
        'list': 'billers.view',
        'retrieve': 'billers.view',
        'create': 'billers.update',
        'update': 'billers.update',
        'partial_update': 'billers.update',
        'destroy': 'billers.update',
    }


# ==================== Payment Services ====================

class PaymentServiceViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = PaymentService.objects.all().order_by('name')
    serializer_class = PaymentServiceSerializer
    required_permissions = {
        'list': 'services.view',
        'retrieve': 'services.view',
        'create': 'services.update',
        'update': 'services.update',
        'partial_update': 'services.update',
        'destroy': 'services.update',
    }


# ==================== Admin Transactions ====================

class AdminTransactionViewSet(PermissionRequiredMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.all().order_by('-created_at')
    serializer_class = AdminTransactionSerializer
    required_permissions = {'list': 'transactions.view', 'retrieve': 'transactions.view'}

    def get_queryset(self):
        qs = Transaction.objects.all().order_by('-created_at')
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(reference__icontains=search) |
                Q(selcom_transid__icontains=search) |
                Q(business__business_name__icontains=search) |
                Q(customer__phone_number__icontains=search)
            )
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        channel = self.request.query_params.get('channel')
        if channel:
            qs = qs.filter(channel=channel)
        business = self.request.query_params.get('business')
        if business:
            qs = qs.filter(business_id=business)
        return qs

    @action(detail=False, methods=['get'])
    @require_permission('transactions.export')
    def export(self, request):
        qs = self.get_queryset()[:10000]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        writer = csv.writer(response)
        writer.writerow(['Reference', 'Business', 'Customer', 'Amount', 'Currency', 'Channel', 'Status', 'Date'])
        for t in qs:
            writer.writerow([
                t.reference, t.business.business_name if t.business else '',
                t.customer.phone_number if t.customer else '',
                t.amount, t.currency, t.channel, t.status, t.created_at
            ])
        log_audit(request.user, 'EXPORT', 'transactions', 'Exported transactions CSV', request=request)
        return response


# ==================== Refunds ====================

class RefundViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = Refund.objects.all().order_by('-created_at')
    serializer_class = RefundSerializer
    required_permissions = {
        'list': 'refunds.view',
        'retrieve': 'refunds.view',
        'create': 'refunds.create',
    }

    def create(self, request, *args, **kwargs):
        txn_id = request.data.get('transaction')
        amount = request.data.get('amount')
        reason = request.data.get('reason')
        if not txn_id or not amount or not reason:
            return Response({'detail': 'transaction, amount, and reason are required.'}, status=status.HTTP_400_BAD_REQUEST)
        txn = get_object_or_404(Transaction, id=txn_id)
        refund = Refund.objects.create(
            transaction=txn,
            amount=amount,
            reason=reason,
            requested_by=request.user,
        )
        log_audit(request.user, 'CREATE', 'refunds', f'Refund requested for {txn.reference}',
                  target_type='Refund', target_id=refund.id, request=request)
        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    @require_permission('refunds.approve')
    def approve(self, request, pk=None):
        refund = self.get_object()
        if refund.status != Refund.Status.REQUESTED:
            return Response({'detail': 'Refund is not in REQUESTED state.'}, status=status.HTTP_400_BAD_REQUEST)
        refund.status = Refund.Status.APPROVED
        refund.approved_by = request.user
        refund.approved_at = timezone.now()
        refund.save(update_fields=['status', 'approved_by', 'approved_at'])
        log_audit(request.user, 'APPROVE', 'refunds', f'Approved refund for {refund.transaction.reference}',
                  target_type='Refund', target_id=refund.id, request=request)
        return Response({'detail': 'Refund approved.'})

    @action(detail=True, methods=['post'])
    @require_permission('refunds.approve')
    def reject(self, request, pk=None):
        refund = self.get_object()
        reason = request.data.get('reason', '')
        refund.status = Refund.Status.REJECTED
        refund.rejection_reason = reason
        refund.approved_by = request.user
        refund.save(update_fields=['status', 'rejection_reason', 'approved_by'])
        log_audit(request.user, 'REJECT', 'refunds', f'Rejected refund for {refund.transaction.reference}',
                  target_type='Refund', target_id=refund.id, request=request)
        return Response({'detail': 'Refund rejected.'})


# ==================== Sales CRM ====================

class SalesLeadViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = SalesLead.objects.all().order_by('-created_at')
    serializer_class = SalesLeadSerializer
    required_permissions = {
        'list': 'sales.view',
        'retrieve': 'sales.view',
        'create': 'sales.create',
        'update': 'sales.update',
        'partial_update': 'sales.update',
        'destroy': 'sales.delete',
    }

    def get_queryset(self):
        qs = SalesLead.objects.all().order_by('-created_at')
        stage = self.request.query_params.get('stage')
        if stage:
            qs = qs.filter(stage=stage)
        assigned = self.request.query_params.get('assigned_to')
        if assigned:
            qs = qs.filter(assigned_to_id=assigned)
        # Sales staff see only their leads unless they have all-branch access
        profile = getattr(self.request.user, 'staff_profile', None)
        if profile and not profile.can_access_all_branches:
            if not profile.has_permission('sales.view_all'):
                qs = qs.filter(Q(assigned_to=self.request.user) | Q(assigned_to__isnull=True))
        return qs


# ==================== Support Tickets ====================

class SupportTicketViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = SupportTicket.objects.select_related('user', 'business', 'assigned_to', 'department').all().order_by('-created_at')
    serializer_class = SupportTicketSerializer
    required_permissions = {
        'list': 'tickets.view',
        'retrieve': 'tickets.view',
        'create': 'tickets.create',
        'update': 'tickets.update',
        'partial_update': 'tickets.update',
    }

    def get_queryset(self):
        qs = SupportTicket.objects.select_related('user', 'business', 'assigned_to', 'department').all().order_by('-created_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        assigned = self.request.query_params.get('assigned_to')
        if assigned:
            qs = qs.filter(assigned_to_id=assigned)
        return qs

    @action(detail=True, methods=['post'])
    @require_permission('tickets.update')
    def assign(self, request, pk=None):
        ticket = self.get_object()
        staff_id = request.data.get('assigned_to')
        if staff_id:
            ticket.assigned_to_id = staff_id
            ticket.status = SupportTicket.Status.IN_PROGRESS
            ticket.save(update_fields=['assigned_to', 'status'])
        return Response({'detail': 'Ticket assigned.'})

    @action(detail=True, methods=['post'])
    @require_permission('tickets.update')
    def resolve(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = SupportTicket.Status.RESOLVED
        ticket.resolved_at = timezone.now()
        ticket.resolution_notes = request.data.get('notes', '')
        ticket.save(update_fields=['status', 'resolved_at', 'resolution_notes'])
        return Response({'detail': 'Ticket resolved.'})

    @action(detail=True, methods=['post'])
    @require_permission('tickets.update')
    def comment(self, request, pk=None):
        ticket = self.get_object()
        comment = TicketComment.objects.create(
            ticket=ticket,
            author=request.user,
            comment=request.data.get('comment', ''),
            is_internal=request.data.get('is_internal', False),
        )
        return Response(TicketCommentSerializer(comment).data, status=status.HTTP_201_CREATED)


# ==================== Notifications ====================

class SystemNotificationViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = SystemNotification.objects.all().order_by('-created_at')
    serializer_class = SystemNotificationSerializer
    required_permissions = {
        'list': 'notifications.view',
        'retrieve': 'notifications.view',
        'create': 'notifications.send',
    }

    def perform_create(self, serializer):
        notification = serializer.save(sent_by=self.request.user, sent_at=timezone.now())
        log_audit(self.request.user, 'CREATE', 'notifications',
                  f'Sent notification: {notification.title}',
                  target_type='SystemNotification', target_id=notification.id,
                  request=self.request)


# ==================== System Settings ====================

class SystemSettingViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    queryset = SystemSetting.objects.all().order_by('key')
    serializer_class = SystemSettingSerializer
    required_permissions = {
        'list': 'settings.view',
        'retrieve': 'settings.view',
        'create': 'settings.update',
        'update': 'settings.update',
        'partial_update': 'settings.update',
        'destroy': 'settings.update',
    }
