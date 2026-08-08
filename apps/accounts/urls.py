from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet, BusinessViewSet, BusinessMemberViewSet,
    OTPVerifyView, PasswordResetRequestView, PasswordResetConfirmView,
    ResendOTPView, CustomTokenObtainPairView
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'businesses', BusinessViewSet)
router.register(r'members', BusinessMemberViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', UserViewSet.as_view({'post': 'create'}), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-otp/', OTPVerifyView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('forgot-password/', PasswordResetRequestView.as_view(), name='forgot-password'),
    path('reset-password/', PasswordResetConfirmView.as_view(), name='reset-password'),
]
