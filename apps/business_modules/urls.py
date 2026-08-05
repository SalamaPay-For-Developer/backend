from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import viewsets, permissions
from apps.business_modules.models import BusinessModule, ModuleFeature, BusinessModuleConfig
from rest_framework import serializers

class ModuleFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleFeature
        fields = '__all__'

class BusinessModuleSerializer(serializers.ModelSerializer):
    features = ModuleFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = BusinessModule
        fields = '__all__'

class BusinessModuleConfigSerializer(serializers.ModelSerializer):
    module = BusinessModuleSerializer(read_only=True)

    class Meta:
        model = BusinessModuleConfig
        fields = '__all__'

class BusinessModuleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BusinessModule.objects.filter(is_active=True)
    serializer_class = BusinessModuleSerializer
    permission_classes = [permissions.AllowAny]

class BusinessModuleConfigViewSet(viewsets.ModelViewSet):
    queryset = BusinessModuleConfig.objects.all()
    serializer_class = BusinessModuleConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

router = DefaultRouter()
router.register(r'available', BusinessModuleViewSet)
router.register(r'configs', BusinessModuleConfigViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
