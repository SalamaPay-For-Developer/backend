from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserViewSet, BusinessViewSet, BusinessMemberViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'businesses', BusinessViewSet)
router.register(r'members', BusinessMemberViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', UserViewSet.as_view({'post': 'create'}), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
