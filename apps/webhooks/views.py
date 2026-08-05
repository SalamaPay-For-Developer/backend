import json
from django.db import transaction as db_transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import WebhookEvent
from apps.payments.models import Transaction
from apps.wallets.models import Wallet, LedgerEntry

@api_view(['POST'])
@permission_classes([AllowAny])
def selcom_webhook(request):
    """
    Handle Selcom Webhook callbacks.
    """
    payload = request.data
    signature = request.headers.get('Digest')
    
    # 1. Log the event
    event = WebhookEvent.objects.create(
        provider=WebhookEvent.Provider.SELCOM,
        event_type=payload.get('event_type', 'payment_notification'),
        payload=payload,
        signature=signature
    )
    
    # 2. Verify signature (logic omitted for brevity, should use SelcomClient method)
    # TODO: Implement signature verification
    
    reference = payload.get('order_id')
    try:
        transaction = Transaction.objects.get(reference=reference)
        event.related_transaction = transaction
        event.save()
        
        if event.processed:
            return Response({"message": "Already processed"}, status=status.HTTP_200_OK)
            
        # 3. Process Result
        res_code = payload.get('resultcode')
        
        with db_transaction.atomic():
            if res_code == '000': # SUCCESS
                if transaction.status != Transaction.Status.SUCCESS:
                    transaction.mark_success(selcom_transid=payload.get('transid'))
                    
                    # 4. Create Ledger Entry (Credit Business Wallet)
                    wallet = Wallet.objects.select_for_update().get(
                        business=transaction.business,
                        wallet_type=Wallet.WalletType.BUSINESS
                    )
                    
                    LedgerEntry.objects.create(
                        wallet=wallet,
                        transaction=transaction,
                        entry_type=LedgerEntry.EntryType.CREDIT,
                        amount=transaction.amount,
                        balance_after=wallet.balance + transaction.amount,
                        narration=f"Collection: {transaction.reference}"
                    )
                    wallet.balance += transaction.amount
                    wallet.save()
            else:
                transaction.mark_failed(payload.get('result', 'Payment failed at provider'))
            
            event.processed = True
            event.save()
            
        return Response({"message": "Webhook processed successfully"}, status=status.HTTP_200_OK)
        
    except Transaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
