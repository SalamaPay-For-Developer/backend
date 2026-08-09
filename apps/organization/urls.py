from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminOverviewView,
    AdminUserViewSet,
    AdminBusinessViewSet,
    PermissionViewSet,
    RoleViewSet,
    DepartmentViewSet,
    BranchViewSet,
    StaffViewSet,
    AuditLogViewSet,
    BusinessTypeConfigViewSet,
    FeeConfigViewSet,
    SettlementFeeViewSet,
    CommissionRuleViewSet,
    BillerViewSet,
    PaymentServiceViewSet,
    AdminTransactionViewSet,
    RefundViewSet,
    SalesLeadViewSet,
    SupportTicketViewSet,
    SystemNotificationViewSet,
    SystemSettingViewSet,
)

router = DefaultRouter()
router.register(r'users', AdminUserViewSet, basename='admin-users')
router.register(r'businesses', AdminBusinessViewSet, basename='admin-businesses')
router.register(r'permissions', PermissionViewSet, basename='permissions')
router.register(r'roles', RoleViewSet, basename='roles')
router.register(r'departments', DepartmentViewSet, basename='departments')
router.register(r'branches', BranchViewSet, basename='branches')
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-logs')
router.register(r'business-types', BusinessTypeConfigViewSet, basename='business-types')
router.register(r'fees', FeeConfigViewSet, basename='fees')
router.register(r'settlement-fees', SettlementFeeViewSet, basename='settlement-fees')
router.register(r'commissions', CommissionRuleViewSet, basename='commissions')
router.register(r'billers', BillerViewSet, basename='billers')
router.register(r'payment-services', PaymentServiceViewSet, basename='payment-services')
router.register(r'transactions', AdminTransactionViewSet, basename='admin-transactions')
router.register(r'refunds', RefundViewSet, basename='refunds')
router.register(r'leads', SalesLeadViewSet, basename='leads')
router.register(r'tickets', SupportTicketViewSet, basename='tickets')
router.register(r'notifications', SystemNotificationViewSet, basename='notifications')
router.register(r'settings', SystemSettingViewSet, basename='settings')

urlpatterns = [
    path('overview/', AdminOverviewView.as_view(), name='admin-overview'),
    path('', include(router.urls)),
]
