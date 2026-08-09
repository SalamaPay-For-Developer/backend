from django.contrib import admin
from .models import (
    Permission, Role, Department, Branch, StaffProfile, AuditLog,
    BusinessTypeConfig, FeeConfig, FeeTier, SettlementFee, CommissionRule,
    Biller, PaymentService, SalesLead, SupportTicket, TicketComment,
    Refund, SystemNotification, SystemSetting,
)

admin.site.register(Permission)
admin.site.register(Role)
admin.site.register(Department)
admin.site.register(Branch)
admin.site.register(StaffProfile)
admin.site.register(AuditLog)
admin.site.register(BusinessTypeConfig)
admin.site.register(FeeConfig)
admin.site.register(FeeTier)
admin.site.register(SettlementFee)
admin.site.register(CommissionRule)
admin.site.register(Biller)
admin.site.register(PaymentService)
admin.site.register(SalesLead)
admin.site.register(SupportTicket)
admin.site.register(TicketComment)
admin.site.register(Refund)
admin.site.register(SystemNotification)
admin.site.register(SystemSetting)
