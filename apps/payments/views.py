import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PaymentCategory, Transaction
from .serializers import (
    PaymentCategorySerializer,
    TransactionSerializer,
    CollectionInitiateSerializer,
    PayoutInitiateSerializer,
    PayoutFeeSerializer,
)
from apps.selcom.client import SelcomClient
from apps.core.sms_service import send_transaction_sms
from apps.core.responses import success_response, error_response
from apps.core.idempotency import IdempotentPostMixin
from asgiref.sync import async_to_sync

MIN_PAYMENT_AMOUNT = Decimal('500')
MIN_PAYOUT_AMOUNT = Decimal('5000')
PAYOUT_FEE_RATE = Decimal('0.02')  # 2% flat fee, min 500 TZS
COLLECTION_FEE_RATE = Decimal('0.012')  # 1.2% per transaction


def calculate_payout_fee(amount: Decimal) -> Decimal:
    fee = (amount * PAYOUT_FEE_RATE).quantize(Decimal('1'))
    return max(fee, Decimal('500'))


def calculate_collection_fee(amount: Decimal) -> Decimal:
    return (amount * COLLECTION_FEE_RATE).quantize(Decimal('0.01'))


class PaymentCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentCategory.objects.all()
    serializer_class = PaymentCategorySerializer
    permission_classes = [permissions.AllowAny]


class TransactionViewSet(IdempotentPostMixin, viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'reference'
    throttle_scope = 'api_v1'

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Transaction.objects.all()
        return Transaction.objects.filter(
            models.Q(customer=user) | models.Q(business__owner=user) | models.Q(business__members__user=user)
        ).distinct()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(response.data, code=200)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return success_response(response.data, code=200)

    @action(detail=False, methods=['post'])
    def collect(self, request):
        """POST /v1/payments/collect — create a mobile money payment intent."""
        cached = self.handle_idempotent_post(request)
        if cached is not None:
            return cached

        serializer = CollectionInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        if data['amount'] < MIN_PAYMENT_AMOUNT:
            return error_response(
                f"amount {data['amount']} is below minimum of {MIN_PAYMENT_AMOUNT}",
                code=400,
            )

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

            response = success_response(TransactionSerializer(transaction).data, code=201)
            self.store_idempotent_response(request, response)
            return response

        except Exception as e:
            transaction.mark_failed(str(e))
            return error_response("Payment initiation failed", code=400, error_code="payment_failed")

    @action(detail=True, methods=['get'])
    def status(self, request, reference=None):
        transaction = self.get_object()
        client = SelcomClient()
        try:
            status_response = async_to_sync(client.order_status)(transaction.reference)
            return success_response(status_response, code=200)
        except Exception as e:
            return error_response(str(e), code=400, error_code="payment_failed")

    @action(detail=True, methods=['get'])
    def receipt(self, request, reference=None):
        """Get receipt data for a transaction."""
        transaction = self.get_object()
        data = TransactionSerializer(transaction).data
        data['date_formatted'] = transaction.completed_at.strftime('%d/%m/%Y %H:%M') if transaction.completed_at else transaction.created_at.strftime('%d/%m/%Y %H:%M')
        data['amount_formatted'] = f"{transaction.amount:,.0f} {transaction.currency}"
        data['fee_amount'] = str(transaction.fee_amount)
        data['fee_formatted'] = f"{transaction.fee_amount:,.0f} {transaction.currency}" if transaction.fee_amount else f"0 {transaction.currency}"
        data['net_amount'] = str(transaction.amount - transaction.fee_amount) if transaction.fee_amount else str(transaction.amount)
        data['net_formatted'] = f"{transaction.amount - transaction.fee_amount:,.0f} {transaction.currency}" if transaction.fee_amount else f"{transaction.amount:,.0f} {transaction.currency}"
        data['type_label'] = dict(Transaction.Type.choices).get(transaction.type, transaction.type)
        data['status_label'] = dict(Transaction.Status.choices).get(transaction.status, transaction.status)
        data['channel_label'] = dict(Transaction.Channel.choices).get(transaction.channel, transaction.channel)
        return success_response(data, code=200)

    @action(detail=False, methods=['get'])
    def fee(self, request):
        """GET /v1/payments/fee?amount=10000 — calculate collection fee."""
        try:
            amount = Decimal(str(request.query_params.get('amount', '0')))
        except Exception:
            return error_response("Invalid amount", code=400, error_code="validation_error")
        if amount <= 0:
            return error_response("Amount must be positive", code=400, error_code="validation_error")
        fee = calculate_collection_fee(amount)
        return success_response({
            "amount": int(amount),
            "fee_amount": float(fee),
            "net_amount": float(amount - fee),
            "fee_rate": "1.2%",
            "currency": "TZS",
        }, code=200)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get transaction summary (income/expense totals)."""
        queryset = self.get_queryset()
        income = queryset.filter(type=Transaction.Type.COLLECTION, status=Transaction.Status.SUCCESS).aggregate(
            total=models.Sum('amount'))['total'] or 0
        expense = queryset.filter(type=Transaction.Type.PAYOUT, status=Transaction.Status.SUCCESS).aggregate(
            total=models.Sum('amount'))['total'] or 0
        count = queryset.count()
        return success_response({
            'total_income': str(income),
            'total_expense': str(expense),
            'total_transactions': count,
        }, code=200)


class PayoutViewSet(IdempotentPostMixin, viewsets.ReadOnlyModelViewSet):
    """
    Disbursements API — /v1/payouts

    POST /v1/payouts/send        Create payout
    GET  /v1/payouts             List payouts
    GET  /v1/payouts/{reference} Get payout status
    GET  /v1/payouts/fee         Calculate payout fee
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'reference'
    throttle_scope = 'api_v1'

    def get_queryset(self):
        user = self.request.user
        base = Transaction.objects.filter(type=Transaction.Type.PAYOUT)
        if user.role == 'ADMIN':
            return base
        return base.filter(
            models.Q(business__owner=user) | models.Q(business__members__user=user)
        ).distinct()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(response.data, code=200)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return success_response(response.data, code=200)

    @action(detail=False, methods=['post'])
    def send(self, request):
        """POST /v1/payouts/send — create a payout to mobile money or bank."""
        cached = self.handle_idempotent_post(request)
        if cached is not None:
            return cached

        serializer = PayoutInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        fee = calculate_payout_fee(data['amount'])
        total = data['amount'] + fee

        business = data['business_id']
        wallet = business.wallets.filter(wallet_type='BUSINESS').first()
        if not wallet or wallet.balance < total:
            available = wallet.balance if wallet else Decimal('0')
            return error_response(
                f"insufficient balance: available {available}, required {total}",
                code=500,
                error_code="payment_failed",
            )

        reference = f"SP-PO-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        channel = Transaction.Channel.BANK if data['channel'] == 'bank' else Transaction.Channel.MPESA

        transaction = Transaction.objects.create(
            reference=reference,
            business=business,
            type=Transaction.Type.PAYOUT,
            amount=data['amount'],
            fee_amount=fee,
            channel=channel,
            status=Transaction.Status.PENDING,
            recipient_name=data['recipient_name'],
            recipient_phone=data.get('recipient_phone', ''),
            recipient_bank=data.get('recipient_bank', ''),
            recipient_account=data.get('recipient_account', ''),
            narration=data.get('narration', ''),
            webhook_url=data.get('webhook_url', ''),
            metadata=data.get('metadata', {}),
        )

        client = SelcomClient()
        try:
            if data['channel'] == 'bank':
                payload = {
                    "transid": reference,
                    "recipientFiCode": data['recipient_bank'],
                    "recipientAccount": data['recipient_account'],
                    "recipientName": data['recipient_name'],
                    "amount": str(data['amount']),
                    "vendor": client.vendor_id,
                    "purpose": data.get('narration', 'Payout'),
                }
                payout_response = async_to_sync(client.qwiksend_process)(payload)
            else:
                payout_response = async_to_sync(client.payout)(
                    transid=reference,
                    amount=int(data['amount']),
                    msisdn=data['recipient_phone'],
                    channel="MPESA",
                )

            transaction.status = Transaction.Status.PROCESSING
            transaction.selcom_transid = payout_response.get('transid', reference)
            transaction.save()

            # Deduct from wallet immediately
            from apps.wallets.models import LedgerEntry
            LedgerEntry.objects.create(
                wallet=wallet,
                transaction=transaction,
                entry_type=LedgerEntry.EntryType.DEBIT,
                amount=total,
                balance_after=wallet.balance - total,
                narration=f"Payout: {reference}"
            )
            wallet.balance -= total
            wallet.save()

            response_data = TransactionSerializer(transaction).data
            response_data['fees'] = {"currency": "TZS", "value": int(fee)}
            response_data['total'] = {"currency": "TZS", "value": int(total)}
            response = success_response(response_data, code=201)
            self.store_idempotent_response(request, response)
            return response

        except Exception:
            transaction.mark_failed("Failed to initiate payout")
            return error_response("Failed to initiate payout", code=500, error_code="PAY_001")

    @action(detail=False, methods=['get'])
    def fee(self, request):
        """GET /v1/payouts/fee?amount=5000"""
        serializer = PayoutFeeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']
        fee_amount = calculate_payout_fee(amount)
        return success_response({
            "amount": int(amount),
            "fee_amount": int(fee_amount),
            "total_amount": int(amount + fee_amount),
            "currency": "TZS",
        }, code=200)
