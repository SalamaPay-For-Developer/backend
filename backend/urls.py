"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from .views import api_home
from apps.developer.views import CheckoutSessionViewSet

sessions_router = DefaultRouter()
sessions_router.register(r'sessions', CheckoutSessionViewSet, basename='sessions')

urlpatterns = [
    path('', api_home, name='api-home'),
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include([
        path('auth/', include('rest_framework.urls')), # DRF default auth
        path('accounts/', include('apps.accounts.urls')),
        path('payments/', include('apps.payments.urls')),
        path('wallets/', include('apps.wallets.urls')),
        path('webhooks/', include('apps.webhooks.urls')),
        path('compliance/', include('apps.compliance.urls')),
        path('modules/', include('apps.business_modules.urls')),
        path('imt/', include('apps.selcom.urls')),
        path('developer/', include('apps.developer.urls')),
        path('admin-panel/', include('apps.organization.urls')),
        # Checkout Sessions & Payment Links API
        path('', include(sessions_router.urls)),
    ])),

    # Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
