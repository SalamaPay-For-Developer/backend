import uuid
from django.db import models
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PaymentCategory, Transaction
from .serializers import (
    PaymentCategorySerializer, 
    TransactionSerializer, 
    CollectionInitiateSerializer
)
from apps.selcom.client import SelcomClient
from asgiref.sync import async_to_sync

class PaymentCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentCategory.objects.all()
    serializer_class = PaymentCategorySerializer
    permission_classes = [permissions.AllowAny]

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'reference'

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Transaction.objects.all()
        return Transaction.objects.filter(
            models.Q(customer=user) | models.Q(business__owner=user) | models.Q(business__members__user=user)
        ).distinct()

    @action(detail=False, methods=['post'])
    def collect(self, request):
        serializer = CollectionInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        reference = f"SP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # 1. Create Internal Transaction
        transaction = Transaction.objects.create(
            reference=reference,
            business=data['business_id'],
            customer=request.user if request.user.is_authenticated else None,
            category=data['category_code'],
            type=Transaction.Type.COLLECTION,
            amount=data['amount'],
            channel=data['channel'],
            payer_msisdn=data['payer_msisdn'],
            status=Transaction.Status.PENDING
        )
        
        # 2. Call Selcom API
        client = SelcomClient()
        try:
            # Create Order
            order_response = async_to_sync(client.create_order)(
                order_id=reference,
                amount=int(data['amount']),
                buyer_phone=data['payer_msisdn'],
                buyer_name=request.user.full_name if request.user.is_authenticated else "Guest"
            )
            
            transaction.selcom_order_id = order_response.get('order_id')
            transaction.payment_token = order_response.get('payment_token')
            transaction.checkout_url = order_response.get('checkout_url')
            transaction.status = Transaction.Status.PROCESSING
            transaction.save()
            
            # 3. If mobile money, trigger push
            if data['channel'] in [Transaction.Channel.MPESA, Transaction.Channel.TIGOPESA, Transaction.Channel.AIRTEL, Transaction.Channel.HALOPESA]:
                async_to_sync(client.wallet_push)(
                    order_id=reference,
                    msisdn=data['payer_msisdn']
                )
            
            return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            transaction.mark_failed(str(e))
            return Response({"error": "Payment initiation failed", "details": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def status(self, request, reference=None):
        transaction = self.get_object()
        client = SelcomClient()
        try:
            status_response = async_to_sync(client.order_status)(transaction.reference)
            return Response(status_response)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
