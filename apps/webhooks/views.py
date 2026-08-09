import hashlib
import hmac
from decimal import Decimal
from django.conf import settings
from django.db import transaction as db_transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import WebhookEvent
from apps.payments.models import Transaction
from apps.wallets.models import Wallet, LedgerEntry
from apps.core.responses import success_response, error_response

COLLECTION_FEE_RATE = Decimal('0.012')  # 1.2%


def verify_selcom_signature(payload: dict, signature: str, signed_fields: list) -> bool:
    """
    Verify the inbound Selcom webhook digest using the same HMAC-SHA256
    scheme as SelcomClient._generate_digest: field1=value1&field2=value2...
    """
    if not signature:
        return False
    signed_data = []
    for field in signed_fields:
        if field in payload:
            signed_data.append(f"{field}={payload[field]}")
    data_string = "&".join(signed_data)
    expected = hmac.new(
        settings.SELCOM_API_SECRET.encode('utf-8'),
        data_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@api_view(['POST'])
@permission_classes([AllowAny])
def selcom_webhook(request):
    """
    Handle Selcom Webhook callbacks (payment.completed / payment.failed).
    """
    payload = request.data
    signature = request.headers.get('Digest')
    signed_fields_header = request.headers.get('Signed-Fields', '')
    signed_fields = [f for f in signed_fields_header.split(',') if f] or ['order_id', 'transid', 'resultcode']

    # 1. Log the event first (always keep an audit trail, even on failed verification)
    event = WebhookEvent.objects.create(
        provider=WebhookEvent.Provider.SELCOM,
        event_type=payload.get('event_type', 'payment_notification'),
        payload=payload,
        signature=signature
    )

    # 2. Verify signature — reject unsigned/invalid webhooks in production
    if not settings.DEBUG:
        if not verify_selcom_signature(payload, signature, signed_fields):
            return error_response("Invalid webhook signature", code=401, error_code="unauthorized")

    reference = payload.get('order_id')
    try:
        transaction = Transaction.objects.get(reference=reference)
        event.related_transaction = transaction
        event.save()

        if event.processed:
            return success_response({"message": "Already processed"}, code=200)

        # 3. Process Result
        res_code = payload.get('resultcode')

        with db_transaction.atomic():
            if res_code == '000':  # SUCCESS
                if transaction.status != Transaction.Status.SUCCESS:
                    transaction.mark_success(selcom_transid=payload.get('transid'))

                    # 4. Calculate 1.2% collection fee and credit net amount
                    fee = (transaction.amount * COLLECTION_FEE_RATE).quantize(Decimal('0.01'))
                    net_amount = transaction.amount - fee

                    # Store fee on transaction
                    transaction.fee_amount = fee
                    transaction.save(update_fields=['fee_amount'])

                    wallet = Wallet.objects.select_for_update().get(
                        business=transaction.business,
                        wallet_type=Wallet.WalletType.BUSINESS
                    )

                    # Credit gross amount
                    LedgerEntry.objects.create(
                        wallet=wallet,
                        transaction=transaction,
                        entry_type=LedgerEntry.EntryType.CREDIT,
                        amount=transaction.amount,
                        balance_after=wallet.balance + transaction.amount,
                        narration=f"Collection: {transaction.reference}"
                    )
                    wallet.balance += transaction.amount

                    # Debit collection fee
                    LedgerEntry.objects.create(
                        wallet=wallet,
                        transaction=transaction,
                        entry_type=LedgerEntry.EntryType.DEBIT,
                        amount=fee,
                        balance_after=wallet.balance - fee,
                        narration=f"Collection fee (1.2%): {transaction.reference}"
                    )
                    wallet.balance -= fee
                    wallet.save()
            else:
                transaction.mark_failed(payload.get('result', 'Payment failed at provider'))

            event.processed = True
            event.save()

        # 5. Fan-out to the merchant's own registered webhook endpoints
        from apps.developer.webhook_service import dispatch_transaction_event
        dispatch_transaction_event(transaction)

        return success_response({"message": "Webhook processed successfully"}, code=200)

    except Transaction.DoesNotExist:
        return error_response("Transaction not found", code=404, error_code="not_found")
    except Exception as e:
        return error_response(str(e), code=400, error_code="validation_error")
