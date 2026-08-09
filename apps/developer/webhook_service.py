"""
Outbound webhook delivery service.

Signs every webhook with HMAC-SHA256 following the SalamaPay/Snippe-style
contract:

    X-Webhook-Signature = hex(HMAC-SHA256(signing_key, "{timestamp}.{raw_body}"))

Headers sent:
    Content-Type:        application/json
    User-Agent:           SalamaPay-Webhook/1.0
    X-Webhook-Event:      e.g. payment.completed
    X-Webhook-Timestamp:  unix timestamp
    X-Webhook-Signature:  hex HMAC-SHA256 signature
"""
import hashlib
import hmac
import json
import time
import uuid

from django.conf import settings
from django.utils import timezone


def sign_payload(secret: str, timestamp: str, raw_body: str) -> str:
    message = f"{timestamp}.{raw_body}"
    return hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()


def build_event_envelope(event_type: str, data: dict) -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": event_type,
        "api_version": getattr(settings, 'SALAMAPAY_API_VERSION', '2026-01-25'),
        "created_at": timezone.now().isoformat(),
        "data": data,
    }


def build_transaction_event_data(transaction) -> dict:
    """Serialize a Transaction into the webhook event data envelope."""
    from apps.payments.models import Transaction as TransactionModel

    net = transaction.amount - (transaction.fee_amount or 0)
    return {
        "reference": str(transaction.id),
        "external_reference": transaction.reference,
        "status": transaction.status.lower(),
        "amount": {"value": int(transaction.amount), "currency": transaction.currency},
        "settlement": {
            "gross": {"value": int(transaction.amount), "currency": transaction.currency},
            "fees": {"value": int(transaction.fee_amount or 0), "currency": transaction.currency},
            "net": {"value": int(net), "currency": transaction.currency},
        },
        "channel": {"type": "mobile_money" if transaction.channel != "BANK" else "bank", "provider": transaction.channel.lower()},
        "metadata": transaction.metadata or {},
        "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None,
    }


def dispatch_transaction_event(transaction):
    """
    Fan-out a transaction status change to all active webhook endpoints
    belonging to the transaction's business workspace.
    """
    from .models import DeveloperWorkspace, WebhookEndpoint
    from .tasks import send_webhook_task

    if not transaction.business:
        return

    workspace = DeveloperWorkspace.objects.filter(business=transaction.business).first()
    if not workspace:
        return

    event_type = {
        "SUCCESS": "payment.completed" if transaction.type == "COLLECTION" else "payout.completed",
        "FAILED": "payment.failed" if transaction.type == "COLLECTION" else "payout.failed",
        "REVERSED": "payout.reversed",
        "EXPIRED": "payment.expired",
    }.get(transaction.status)

    if not event_type:
        return

    data = build_transaction_event_data(transaction)
    endpoints = WebhookEndpoint.objects.filter(workspace=workspace, status=WebhookEndpoint.Status.ACTIVE)

    for endpoint in endpoints:
        if endpoint.events and event_type not in endpoint.events:
            continue
        send_webhook_task.delay(str(endpoint.id), event_type, data)
