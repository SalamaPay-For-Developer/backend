from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DeveloperWorkspaceView,
    DeveloperOverviewView,
    ConnectSelcomView,
    SelcomConnectionView,
    ApiKeyViewSet,
    WebhookEndpointViewSet,
    CheckoutSessionViewSet,
    ApiLogViewSet,
    ServiceCapabilityViewSet,
    public_checkout_view,
)

router = DefaultRouter()
router.register(r'api-keys', ApiKeyViewSet, basename='api-keys')
router.register(r'webhooks', WebhookEndpointViewSet, basename='webhooks')
router.register(r'checkouts', CheckoutSessionViewSet, basename='checkouts')
router.register(r'logs', ApiLogViewSet, basename='logs')
router.register(r'services', ServiceCapabilityViewSet, basename='services')

urlpatterns = [
    path('workspace/', DeveloperWorkspaceView.as_view(), name='workspace'),
    path('overview/', DeveloperOverviewView.as_view(), name='overview'),
    path('connect-selcom/', ConnectSelcomView.as_view(), name='connect-selcom'),
    path('selcom/', SelcomConnectionView.as_view(), name='selcom-connection'),
    path('selcom/test/', SelcomConnectionView.test, name='selcom-test'),
    path('checkout/<str:code>/', public_checkout_view, name='public-checkout'),
    path('', include(router.urls)),
]
