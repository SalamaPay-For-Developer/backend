from django.contrib import admin
from .models import (
    DeveloperWorkspace,
    SelcomCredential,
    SalamaPayApiKey,
    WebhookEndpoint,
    WebhookDelivery,
    CheckoutSession,
    ApiLog,
    ServiceCapability,
)

admin.site.register(DeveloperWorkspace)
admin.site.register(SelcomCredential)
admin.site.register(SalamaPayApiKey)
admin.site.register(WebhookEndpoint)
admin.site.register(WebhookDelivery)
admin.site.register(CheckoutSession)
admin.site.register(ApiLog)
admin.site.register(ServiceCapability)
