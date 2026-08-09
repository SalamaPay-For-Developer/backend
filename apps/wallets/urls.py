from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WalletViewSet, LedgerEntryViewSet, SavingsGoalViewSet

router = DefaultRouter()
router.register(r'wallets', WalletViewSet)
router.register(r'ledger', LedgerEntryViewSet)
router.register(r'savings', SavingsGoalViewSet, basename='savings-goal')

urlpatterns = [
    path('', include(router.urls)),
]
