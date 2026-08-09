import json
import time

import httpx
from celery import shared_task
from django.utils import timezone

from .webhook_service import sign_payload, build_event_envelope

# Exponential backoff schedule (seconds) matching the Snippe retry contract:
# 1: immediate, 2: 3min, 3: 6min, 4: 12min, 5: 24min
RETRY_SCHEDULE_SECONDS = [0, 180, 360, 720, 1440]
MAX_ATTEMPTS = len(RETRY_SCHEDULE_SECONDS)


@shared_task(bind=True, max_retries=MAX_ATTEMPTS - 1)
def send_webhook_task(self, endpoint_id: str, event_type: str, data: dict):
    from .models import WebhookEndpoint, WebhookDelivery

    try:
        endpoint = WebhookEndpoint.objects.get(id=endpoint_id)
    except WebhookEndpoint.DoesNotExist:
        return

    envelope = build_event_envelope(event_type, data)
    raw_body = json.dumps(envelope, sort_keys=True, default=str)
    timestamp = str(int(time.time()))
    signature = sign_payload(endpoint.secret or "", timestamp, raw_body)

    delivery, _ = WebhookDelivery.objects.get_or_create(
        endpoint=endpoint,
        event_type=event_type,
        transaction_ref=data.get('external_reference', ''),
        defaults={"payload": envelope, "status": WebhookDelivery.Status.PENDING},
    )
    delivery.attempt_count += 1

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SalamaPay-Webhook/1.0",
        "X-Webhook-Event": event_type,
        "X-Webhook-Timestamp": timestamp,
        "X-Webhook-Signature": signature,
    }

    try:
        response = httpx.post(endpoint.url, content=raw_body, headers=headers, timeout=30)
        delivery.response_status = response.status_code
        delivery.response_body = response.text[:2000]

        endpoint.total_deliveries += 1

        if 200 <= response.status_code < 300:
            delivery.status = WebhookDelivery.Status.DELIVERED
            delivery.delivered_at = timezone.now()
            endpoint.successful_deliveries += 1
            endpoint.save(update_fields=['total_deliveries', 'successful_deliveries'])
            delivery.save()
            return

        endpoint.failed_deliveries += 1
        endpoint.save(update_fields=['total_deliveries', 'failed_deliveries'])
        raise httpx.HTTPStatusError("Non-2xx response", request=response.request, response=response)

    except Exception as exc:
        delivery.status = WebhookDelivery.Status.RETRYING if self.request.retries < MAX_ATTEMPTS - 1 else WebhookDelivery.Status.FAILED
        delivery.error_message = str(exc)
        delivery.save()

        if self.request.retries < MAX_ATTEMPTS - 1:
            countdown = RETRY_SCHEDULE_SECONDS[self.request.retries + 1]
            raise self.retry(exc=exc, countdown=countdown)
