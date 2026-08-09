from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentCategoryViewSet, TransactionViewSet, PayoutViewSet

router = DefaultRouter()
router.register(r'categories', PaymentCategoryViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'payouts', PayoutViewSet, basename='payouts')

urlpatterns = [
    path('', include(router.urls)),
]
