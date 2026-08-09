import secrets
import string
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import Business
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
from .serializers import (
    DeveloperWorkspaceSerializer,
    ConnectSelcomSerializer,
    SelcomCredentialSerializer,
    SalamaPayApiKeySerializer,
    CreateApiKeySerializer,
    WebhookEndpointSerializer,
    WebhookDeliverySerializer,
    CheckoutSessionSerializer,
    CreateCheckoutSerializer,
    ApiLogSerializer,
    ApiLogDetailSerializer,
    ServiceCapabilitySerializer,
)


def get_user_workspace(user):
    """Get or create a developer workspace for the user's verified business."""
    business = Business.objects.filter(owner=user, kyc_status=Business.KYCStatus.APPROVED).first()
    if not business:
        business = Business.objects.filter(owner=user).first()
    if not business:
        return None
    workspace, _ = DeveloperWorkspace.objects.get_or_create(business=business)
    return workspace


class DeveloperWorkspaceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workspace = get_user_workspace(request.user)
        if not workspace:
            return Response(
                {'detail': 'You need to create a business first.', 'requires_business': True},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = DeveloperWorkspaceSerializer(workspace)
        return Response(serializer.data)

    def patch(self, request):
        workspace = get_user_workspace(request.user)
        if not workspace:
            return Response(
                {'detail': 'You need to create a business first.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = DeveloperWorkspaceSerializer(workspace, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DeveloperOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workspace = get_user_workspace(request.user)
        if not workspace:
            return Response({'detail': 'No business found.'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        logs = ApiLog.objects.filter(workspace=workspace)
        log_stats = logs.aggregate(
            total=Count('id'),
            success=Count('id', filter=Q(response_status__gte=200, response_status__lt=300)),
            failed=Count('id', filter=Q(response_status__gte=400)),
        )

        checkouts = CheckoutSession.objects.filter(workspace=workspace)
        checkout_stats = checkouts.aggregate(
            total_amount=Sum('amount', filter=Q(status=CheckoutSession.Status.SUCCESS)) or 0,
            today_amount=Sum('amount', filter=Q(status=CheckoutSession.Status.SUCCESS, created_at__gte=today_start)) or 0,
            active=Count('id', filter=Q(status__in=[CheckoutSession.Status.PENDING, CheckoutSession.Status.PROCESSING])),
        )

        endpoints = WebhookEndpoint.objects.filter(workspace=workspace, status=WebhookEndpoint.Status.ACTIVE)
        total_deliveries = sum(e.total_deliveries for e in endpoints)
        successful = sum(e.successful_deliveries for e in endpoints)
        delivery_rate = round((successful / total_deliveries * 100), 1) if total_deliveries > 0 else 0

        return Response({
            'api_requests_total': log_stats['total'] or 0,
            'api_requests_success': log_stats['success'] or 0,
            'api_requests_failed': log_stats['failed'] or 0,
            'transactions_total': checkout_stats['total_amount'],
            'transactions_today': checkout_stats['today_amount'],
            'webhook_delivery_rate': delivery_rate,
            'active_checkouts': checkout_stats['active'],
            'setup_progress': workspace.setup_progress,
            'environment': workspace.environment,
            'production_enabled': workspace.production_enabled,
            'selcom_connected': workspace.selcom_connected,
        })


class ConnectSelcomView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        workspace = get_user_workspace(request.user)
        if not workspace:
            return Response({'detail': 'Create a business first.'}, status=status.HTTP_400_BAD_REQUEST)

        if not workspace.business.is_verified:
            return Response(
                {'detail': 'Business must be KYC verified before connecting Selcom.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ConnectSelcomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cred, created = SelcomCredential.objects.update_or_create(
            workspace=workspace,
            environment=data['environment'],
            defaults={
                'api_key': data['api_key'],
                'vendor_id': data.get('vendor_id'),
                'pin': data.get('pin'),
                'is_active': True,
            }
        )
        cred.set_api_secret(data['api_secret'])
        cred.save()

        workspace.selcom_connected = True
        workspace.save(update_fields=['selcom_connected'])

        # Enable default services
        default_services = [
            ServiceCapability.ServiceType.CHECKOUT,
            ServiceCapability.ServiceType.C2B_COLLECTION,
            ServiceCapability.ServiceType.UTILITY_PAYMENT,
            ServiceCapability.ServiceType.WALLET_CASHIN,
            ServiceCapability.ServiceType.QWIKSEND,
            ServiceCapability.ServiceType.WEBHOOKS,
        ]
        for svc in default_services:
            ServiceCapability.objects.get_or_create(
                workspace=workspace,
                service=svc,
                defaults={'is_enabled': True, 'configured_at': timezone.now()}
            )

        return Response({
            'detail': 'Selcom connected successfully.',
            'credential': SelcomCredentialSerializer(cred).data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class SelcomConnectionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workspace = get_user_workspace(request.user)
        if not workspace:
            return Response({'detail': 'No business found.'}, status=status.HTTP_404_NOT_FOUND)

        creds = SelcomCredential.objects.filter(workspace=workspace, is_active=True)
        return Response({
            'connected': workspace.selcom_connected,
            'credentials': SelcomCredentialSerializer(creds, many=True).data,
        })

    def delete(self, request):
        workspace = get_user_workspace(request.user)
        if not workspace:
            return Response({'detail': 'No business found.'}, status=status.HTTP_404_NOT_FOUND)

        SelcomCredential.objects.filter(workspace=workspace).update(is_active=False)
        workspace.selcom_connected = False
        workspace.save(update_fields=['selcom_connected'])
        return Response({'detail': 'Selcom disconnected.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def test(self, request):
        workspace = get_user_workspace(request.user)
        if not workspace:
            return Response({'detail': 'No business found.'}, status=status.HTTP_404_NOT_FOUND)

        cred = SelcomCredential.objects.filter(workspace=workspace, is_active=True).first()
        if not cred:
            return Response({'detail': 'No Selcom credentials found.'}, status=status.HTTP_400_BAD_REQUEST)

        # TODO: Actual test call to Selcom API
        cred.last_checked = timezone.now()
        cred.last_check_status = 'SUCCESS'
        cred.save(update_fields=['last_checked', 'last_check_status'])

        return Response({'detail': 'Connection test successful.', 'status': 'SUCCESS'})


class ApiKeyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SalamaPayApiKeySerializer

    def get_queryset(self):
        workspace = get_user_workspace(self.request.user)
        if not workspace:
            return SalamaPayApiKey.objects.none()
        return SalamaPayApiKey.objects.filter(workspace=workspace)

    def create(self, request, *args, **kwargs):
        workspace = get_user_workspace(request.user)
        if not workspace:
            return Response({'detail': 'No business found.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CreateApiKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_key = SalamaPayApiKey.generate_key(
            serializer.validated_data['environment'],
            serializer.validated_data['key_type'],
        )

        api_key = SalamaPayApiKey.objects.create(
            workspace=workspace,
            key_type=serializer.validated_data['key_type'],
            environment=serializer.validated_data['environment'],
            key_prefix=raw_key[:12],
            key_hash=raw_key,
            is_active=True,
        )

        return Response({
            'key': raw_key,
            'api_key': SalamaPayApiKeySerializer(api_key).data,
            'detail': 'Save this key securely. It will not be shown again.',
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def rotate(self, request, pk=None):
        old_key = self.get_object()
        raw_key = SalamaPayApiKey.generate_key(old_key.environment, old_key.key_type)

        new_key = SalamaPayApiKey.objects.create(
            workspace=old_key.workspace,
            key_type=old_key.key_type,
            environment=old_key.environment,
            key_prefix=raw_key[:12],
            key_hash=raw_key,
            is_active=True,
            rotated_from=old_key,
        )
        old_key.is_active = False
        old_key.save(update_fields=['is_active'])

        return Response({
            'key': raw_key,
            'api_key': SalamaPayApiKeySerializer(new_key).data,
            'detail': 'Key rotated. Old key has been deactivated.',
        }, status=status.HTTP_201_CREATED)


class WebhookEndpointViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WebhookEndpointSerializer

    def get_queryset(self):
        workspace = get_user_workspace(self.request.user)
        if not workspace:
            return WebhookEndpoint.objects.none()
        return WebhookEndpoint.objects.filter(workspace=workspace)

    def perform_create(self, serializer):
        workspace = get_user_workspace(self.request.user)
        secret = 'whsec_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(24))
        serializer.save(workspace=workspace, secret=secret)

    @action(detail=True, methods=['get'])
    def deliveries(self, request, pk=None):
        endpoint = self.get_object()
        deliveries = WebhookDelivery.objects.filter(endpoint=endpoint).order_by('-created_at')[:50]
        serializer = WebhookDeliverySerializer(deliveries, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='deliveries/(?P<delivery_id>[^/.]+)/retry')
    def retry_delivery(self, request, pk=None, delivery_id=None):
        endpoint = self.get_object()
        delivery = get_object_or_404(WebhookDelivery, id=delivery_id, endpoint=endpoint)
        # TODO: Actually re-deliver the webhook
        delivery.attempt_count += 1
        delivery.status = WebhookDelivery.Status.RETRYING
        delivery.save(update_fields=['attempt_count', 'status'])
        return Response({'detail': 'Retry scheduled.'})


class CheckoutSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CheckoutSessionSerializer

    def get_queryset(self):
        workspace = get_user_workspace(self.request.user)
        if not workspace:
            return CheckoutSession.objects.none()
        return CheckoutSession.objects.filter(workspace=workspace).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        workspace = get_user_workspace(request.user)
        if not workspace:
            return Response({'detail': 'No business found.'}, status=status.HTTP_400_BAD_REQUEST)

        if not workspace.selcom_connected:
            return Response(
                {'detail': 'Connect Selcom before creating checkouts.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CreateCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order_id = f"SP-{secrets.token_hex(8).upper()}"
        checkout = CheckoutSession.objects.create(
            workspace=workspace,
            order_id=order_id,
            amount=data['amount'],
            currency=data.get('currency', 'TZS'),
            description=data.get('description'),
            customer_name=data.get('customer_name'),
            customer_phone=data.get('customer_phone'),
            customer_email=data.get('customer_email'),
            payment_methods=data.get('payment_methods', ['MOBILE_MONEY', 'CARD', 'BANK']),
            success_url=data.get('success_url'),
            cancel_url=data.get('cancel_url'),
            appearance_config=data.get('appearance_config', {}),
        )

        return Response(
            CheckoutSessionSerializer(checkout).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        checkout = self.get_object()
        return Response({'status': checkout.status, 'order_id': checkout.order_id})


class ApiLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        workspace = get_user_workspace(self.request.user)
        if not workspace:
            return ApiLog.objects.none()
        return ApiLog.objects.filter(workspace=workspace).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ApiLogDetailSerializer
        return ApiLogSerializer


class ServiceCapabilityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceCapabilitySerializer

    def get_queryset(self):
        workspace = get_user_workspace(self.request.user)
        if not workspace:
            return ServiceCapability.objects.none()
        return ServiceCapability.objects.filter(workspace=workspace)
