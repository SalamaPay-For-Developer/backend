from django.urls import path
from .views import selcom_webhook

urlpatterns = [
    path('selcom/', selcom_webhook, name='selcom_webhook'),
]
