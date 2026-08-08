from django.contrib import admin
from .models import SMSLog


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('phone', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('phone', 'message')
    readonly_fields = ('response', 'created_at', 'updated_at')
    ordering = ('-created_at',)
