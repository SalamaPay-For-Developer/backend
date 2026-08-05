import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

class SelcomClient:
    def __init__(self):
        self.base_url = settings.SELCOM_BASE_URL
        self.api_key = settings.SELCOM_API_KEY
        self.api_secret = settings.SELCOM_API_SECRET
        self.vendor_id = settings.SELCOM_VENDOR_ID

    def _generate_digest(self, payload: dict, signed_fields: list) -> str:
        """
        Generate HMAC-SHA256 digest for Selcom API.
        Format: field1=value1&field2=value2...
        """
        signed_data = []
        for field in signed_fields:
            if field in payload:
                signed_data.append(f"{field}={payload[field]}")
        
        data_string = "&".join(signed_data)
        digest = hmac.new(
            self.api_secret.encode('utf-8'),
            data_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return digest

    def _get_headers(self, payload: dict, signed_fields: list) -> dict:
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00')
        digest = self._generate_digest(payload, signed_fields)
        
        auth_string = f"SELCOM {base64.b64encode(self.api_key.encode()).decode()}"
        
        return {
            "Authorization": auth_string,
            "Digest-Method": "HS256",
            "Digest": digest,
            "Timestamp": timestamp,
            "Signed-Fields": ",".join(signed_fields),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def create_order(self, order_id, amount, buyer_phone, buyer_name=None, buyer_email=None):
        endpoint = f"{self.base_url}/checkout/create-order"
        payload = {
            "vendor": self.vendor_id,
            "order_id": order_id,
            "buyer_name": buyer_name or "SalamaPay Customer",
            "buyer_phone": buyer_phone,
            "buyer_email": buyer_email or "customer@salamapay.tz",
            "amount": str(amount),
            "currency": "TZS",
            "no_of_items": 1,
            "webhook_url": settings.SELCOM_WEBHOOK_URL
        }
        signed_fields = ["vendor", "order_id", "buyer_phone", "amount", "currency"]
        
        headers = self._get_headers(payload, signed_fields)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (create_order): {e}")
                raise

    async def wallet_push(self, order_id, msisdn):
        """Trigger USSD Push for Mobile Money."""
        endpoint = f"{self.base_url}/checkout/wallet-push"
        payload = {
            "vendor": self.vendor_id,
            "order_id": order_id,
            "msisdn": msisdn
        }
        signed_fields = ["vendor", "order_id", "msisdn"]
        
        headers = self._get_headers(payload, signed_fields)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (wallet_push): {e}")
                raise

    async def order_status(self, order_id):
        endpoint = f"{self.base_url}/checkout/order-status"
        payload = {
            "vendor": self.vendor_id,
            "order_id": order_id
        }
        signed_fields = ["vendor", "order_id"]
        
        headers = self._get_headers(payload, signed_fields)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (order_status): {e}")
                raise

    async def payout(self, transid, amount, msisdn, channel):
        """Disbursement / Payout API."""
        endpoint = f"{self.base_url}/disbursement/payout"
        payload = {
            "vendor": self.vendor_id,
            "transid": transid,
            "msisdn": msisdn,
            "amount": str(amount),
            "currency": "TZS",
            "channel": channel # e.g. MPESA, TIGOPESA
        }
        signed_fields = ["vendor", "transid", "msisdn", "amount", "currency"]
        
        headers = self._get_headers(payload, signed_fields)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (payout): {e}")
                raise
