"""
Idempotency-Key support for POST requests, matching the Snippe-style contract:

- Header: Idempotency-Key
- Max length: 30 characters (returns 500 PAY_001-style error if exceeded, we use 400)
- Valid for 24 hours
- Same key + same request body -> returns the cached response
- Same key + different body -> returns 422 error
"""
import hashlib
import json
from datetime import timedelta

from django.utils import timezone

from apps.core.models import IdempotencyRecord
from apps.core.responses import error_response

MAX_IDEMPOTENCY_KEY_LENGTH = 30
IDEMPOTENCY_KEY_TTL_HOURS = 24


def _hash_body(data) -> str:
    payload = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


class IdempotentPostMixin:
    """
    Mixin for DRF views/viewsets. Wrap the actual create logic in
    `perform_idempotent_create(self, request)` and call
    `self.handle_idempotent_post(request)` from your `create`/`post` method.
    """

    def handle_idempotent_post(self, request):
        key = request.headers.get('Idempotency-Key')
        endpoint = request.path

        if not key:
            return None  # No idempotency key supplied, proceed normally

        if len(key) > MAX_IDEMPOTENCY_KEY_LENGTH:
            return error_response(
                f"Idempotency-Key exceeds {MAX_IDEMPOTENCY_KEY_LENGTH} character limit.",
                code=500,
                error_code="PAY_001",
            )

        request_hash = _hash_body(request.data)

        existing = IdempotencyRecord.objects.filter(key=key, endpoint=endpoint).first()
        if existing:
            if existing.is_expired:
                existing.delete()
            elif existing.request_hash != request_hash:
                return error_response(
                    "idempotency key already used with different request body",
                    code=422,
                    error_code="validation_error",
                )
            else:
                from rest_framework.response import Response
                return Response(existing.response_body, status=existing.response_status)

        return None

    def store_idempotent_response(self, request, response):
        key = request.headers.get('Idempotency-Key')
        if not key or len(key) > MAX_IDEMPOTENCY_KEY_LENGTH:
            return
        IdempotencyRecord.objects.update_or_create(
            key=key,
            endpoint=request.path,
            defaults={
                'request_hash': _hash_body(request.data),
                'response_status': response.status_code,
                'response_body': response.data,
                'expires_at': timezone.now() + timedelta(hours=IDEMPOTENCY_KEY_TTL_HOURS),
            }
        )
