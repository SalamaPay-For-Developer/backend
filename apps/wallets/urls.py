from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WalletViewSet, LedgerEntryViewSet

router = DefaultRouter()
router.register(r'wallets', WalletViewSet)
router.register(r'ledger', LedgerEntryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
