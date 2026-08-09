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

    async def wallet_name_lookup(self, utilitycode, utilityref, transid):
        """IMT Wallet Name Lookup - GET /v1/imt/wallet-namelookup"""
        endpoint = f"{self.base_url}/imt/wallet-namelookup"
        params = {
            "utilitycode": utilitycode,
            "utilityref": utilityref,
            "transid": transid,
        }
        signed_fields = ["utilitycode", "utilityref", "transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (wallet_name_lookup): {e}")
                raise

    async def bank_name_lookup(self, bank, account, transid):
        """IMT Bank Account Name Lookup - GET /v1/imt/bank-namelookup/"""
        endpoint = f"{self.base_url}/imt/bank-namelookup/"
        params = {
            "bank": bank,
            "account": account,
            "transid": transid,
        }
        signed_fields = ["bank", "account", "transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (bank_name_lookup): {e}")
                raise

    async def send_money(self, payload):
        """IMT Send Money - POST /v1/imt/send-money"""
        endpoint = f"{self.base_url}/imt/send-money"
        signed_fields = [
            "messageId", "end2endId", "vendor", "pin",
            "currency", "amount", "billingAmount", "billingCurrency", "purpose"
        ]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (send_money): {e}")
                raise

    async def imt_transaction_status(self, message_id):
        """IMT Transaction Status - GET /v1/imt/query"""
        endpoint = f"{self.base_url}/imt/query"
        params = {
            "messageId": message_id,
        }
        signed_fields = ["messageId"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (imt_transaction_status): {e}")
                raise

    # ==================== Utility Payments ====================

    async def utility_payment(self, transid, utilitycode, utilityref, amount, pin, msisdn=None):
        """Utility Payment Request - POST /v1/utilitypayment/process"""
        endpoint = f"{self.base_url}/utilitypayment/process"
        payload = {
            "transid": transid,
            "utilitycode": utilitycode,
            "utilityref": utilityref,
            "amount": str(amount),
            "vendor": self.vendor_id,
            "pin": pin,
        }
        if msisdn:
            payload["msisdn"] = msisdn
        signed_fields = ["transid", "utilitycode", "utilityref", "amount", "vendor", "pin"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (utility_payment): {e}")
                raise

    async def utility_lookup(self, utilitycode, utilityref, transid):
        """Utility Lookup - GET /v1/utilitypayment/lookup"""
        endpoint = f"{self.base_url}/utilitypayment/lookup"
        params = {
            "utilitycode": utilitycode,
            "utilityref": utilityref,
            "transid": transid,
        }
        signed_fields = ["utilitycode", "utilityref", "transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (utility_lookup): {e}")
                raise

    async def utility_payment_status(self, transid):
        """Utility Payment Status - GET /v1/utilitypayment/query"""
        endpoint = f"{self.base_url}/utilitypayment/query"
        params = {"transid": transid}
        signed_fields = ["transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (utility_payment_status): {e}")
                raise

    # ==================== Wallet Cashin ====================

    async def wallet_cashin(self, transid, utilitycode, utilityref, amount, pin, msisdn=None):
        """Wallet Cashin - POST /v1/walletcashin/process"""
        endpoint = f"{self.base_url}/walletcashin/process"
        payload = {
            "transid": transid,
            "utilitycode": utilitycode,
            "utilityref": utilityref,
            "amount": str(amount),
            "vendor": self.vendor_id,
            "pin": pin,
        }
        if msisdn:
            payload["msisdn"] = msisdn
        signed_fields = ["transid", "utilitycode", "utilityref", "amount", "vendor", "pin"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (wallet_cashin): {e}")
                raise

    async def wallet_cashin_name_lookup(self, utilitycode, utilityref, transid):
        """Wallet Cashin Name Lookup - GET /v1/walletcashin/namelookup"""
        endpoint = f"{self.base_url}/walletcashin/namelookup"
        params = {
            "utilitycode": utilitycode,
            "utilityref": utilityref,
            "transid": transid,
        }
        signed_fields = ["utilitycode", "utilityref", "transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (wallet_cashin_name_lookup): {e}")
                raise

    async def wallet_cashin_status(self, transid):
        """Wallet Cashin Status - GET /v1/walletcashin/query"""
        endpoint = f"{self.base_url}/walletcashin/query"
        params = {"transid": transid}
        signed_fields = ["transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (wallet_cashin_status): {e}")
                raise

    # ==================== Selcom Pesa ====================

    async def selcompesa_cashin(self, transid, utilityref, amount, pin, msisdn=None):
        """Selcom Pesa Cashin - POST /v1/selcompesa/cashin"""
        endpoint = f"{self.base_url}/selcompesa/cashin"
        payload = {
            "transid": transid,
            "utilityref": utilityref,
            "utilitycode": "SPSCASHIN",
            "amount": str(amount),
            "vendor": self.vendor_id,
            "pin": pin,
        }
        if msisdn:
            payload["msisdn"] = msisdn
        signed_fields = ["transid", "utilityref", "utilitycode", "amount", "vendor", "pin"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (selcompesa_cashin): {e}")
                raise

    async def selcompesa_name_lookup(self, utilityref, transid):
        """Selcom Pesa Name Lookup - GET /v1/selcompesa/namelookup"""
        endpoint = f"{self.base_url}/selcompesa/namelookup"
        params = {
            "utilityref": utilityref,
            "transid": transid,
        }
        signed_fields = ["utilityref", "transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (selcompesa_name_lookup): {e}")
                raise

    async def selcompesa_status(self, transid):
        """Selcom Pesa Status - GET /v1/selcompesa/query"""
        endpoint = f"{self.base_url}/selcompesa/query"
        params = {"transid": transid}
        signed_fields = ["transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (selcompesa_status): {e}")
                raise

    # ==================== Agent Cashout ====================

    async def agent_cashout(self, transid, utilityref, amount, pin, name=None):
        """Agent Cashout - POST /v1/hudumacashin/process"""
        endpoint = f"{self.base_url}/hudumacashin/process"
        payload = {
            "transid": transid,
            "utilitycode": "HUDUMACI",
            "utilityref": utilityref,
            "amount": str(amount),
            "vendor": self.vendor_id,
            "pin": pin,
        }
        if name:
            payload["name"] = name
        signed_fields = ["transid", "utilitycode", "utilityref", "amount", "vendor", "pin"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (agent_cashout): {e}")
                raise

    async def agent_cashout_status(self, transid):
        """Agent Cashout Status - GET /v1/hudumacashin/query"""
        endpoint = f"{self.base_url}/hudumacashin/query"
        params = {"transid": transid}
        signed_fields = ["transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (agent_cashout_status): {e}")
                raise

    # ==================== Float Account ====================

    async def float_balance(self, pin, transid):
        """Get Float Balance - POST /v1/vendor/balance"""
        endpoint = f"{self.base_url}/vendor/balance"
        payload = {
            "vendor": self.vendor_id,
            "pin": pin,
            "transid": transid,
        }
        signed_fields = ["vendor", "pin", "transid"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (float_balance): {e}")
                raise

    # ==================== Qwiksend (Bank Transfer) ====================

    async def qwiksend_process(self, payload):
        """Bank Transfer - POST /v1/qwiksend/process"""
        endpoint = f"{self.base_url}/qwiksend/process"
        signed_fields = [
            "transid", "recipientFiCode", "recipientAccount",
            "recipientName", "senderAccount", "senderName",
            "amount", "vendor", "pin", "msisdn", "purpose"
        ]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (qwiksend_process): {e}")
                raise

    async def qwiksend_lookup(self, bank, account, transid):
        """Bank Account Name Lookup - GET /v1/qwiksend/lookup/"""
        endpoint = f"{self.base_url}/qwiksend/lookup/"
        params = {
            "bank": bank,
            "account": account,
            "transid": transid,
        }
        signed_fields = ["bank", "account", "transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (qwiksend_lookup): {e}")
                raise

    async def qwiksend_status(self, transid):
        """Qwiksend Status - GET /v1/qwiksend/query"""
        endpoint = f"{self.base_url}/qwiksend/query"
        params = {"transid": transid}
        signed_fields = ["transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (qwiksend_status): {e}")
                raise

    # ==================== VCN ====================

    async def vcn_create(self, payload):
        """Create VCN - POST /v1/vcn/create"""
        endpoint = f"{self.base_url}/vcn/create"
        signed_fields = [
            "msisdn", "account", "first_name", "last_name",
            "gender", "dob", "address", "city", "nationality",
            "vendor", "pin", "transid"
        ]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (vcn_create): {e}")
                raise

    async def vcn_create_status(self, msisdn, transid):
        """VCN Create Status - GET /v1/vcn/create-status-enquiry"""
        endpoint = f"{self.base_url}/vcn/create-status-enquiry"
        params = {"msisdn": msisdn, "transid": transid}
        signed_fields = ["msisdn", "transid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (vcn_create_status): {e}")
                raise

    async def vcn_change_status(self, payload):
        """Block/Unblock/Suspend VCN - POST /v1/vcn/changestatus"""
        endpoint = f"{self.base_url}/vcn/changestatus"
        signed_fields = ["msisdn", "account", "status", "requestid"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (vcn_change_status): {e}")
                raise

    async def vcn_show(self, payload):
        """Show VCN - POST /v1/vcn/show"""
        endpoint = f"{self.base_url}/vcn/show"
        signed_fields = ["msisdn", "account", "requestid"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (vcn_show): {e}")
                raise

    async def vcn_status(self, msisdn, account):
        """Get VCN Status - GET /v1/vcn/status"""
        endpoint = f"{self.base_url}/vcn/status"
        params = {"msisdn": msisdn, "account": account}
        signed_fields = ["msisdn", "account"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (vcn_status): {e}")
                raise

    async def vcn_set_limit(self, payload):
        """Set VCN Transaction Limit - POST /v1/vcn/set-limit"""
        endpoint = f"{self.base_url}/vcn/set-limit"
        signed_fields = ["msisdn", "account", "limit_amount", "limit_type"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (vcn_set_limit): {e}")
                raise

    # ==================== Checkout ====================

    async def create_order_minimal(self, payload):
        """Create Order Minimal - POST /v1/checkout/create-order-minimal"""
        endpoint = f"{self.base_url}/checkout/create-order-minimal"
        signed_fields = ["vendor", "order_id", "buyer_phone", "amount", "currency"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (create_order_minimal): {e}")
                raise

    async def cancel_order(self, order_id):
        """Cancel Order - DELETE /v1/checkout/cancel-order"""
        endpoint = f"{self.base_url}/checkout/cancel-order"
        params = {"order_id": order_id}
        signed_fields = ["order_id"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (cancel_order): {e}")
                raise

    async def list_orders(self, fromdate, todate):
        """List Orders - GET /v1/checkout/list-orders"""
        endpoint = f"{self.base_url}/checkout/list-orders"
        params = {"fromdate": fromdate, "todate": todate}
        signed_fields = ["fromdate", "todate"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (list_orders): {e}")
                raise

    async def stored_cards(self, buyer_userid, gateway_buyer_uuid):
        """Fetch Stored Cards - GET /v1/checkout/stored-cards"""
        endpoint = f"{self.base_url}/checkout/stored-cards"
        params = {"buyer_userid": buyer_userid, "gateway_buyer_uuid": gateway_buyer_uuid}
        signed_fields = ["buyer_userid", "gateway_buyer_uuid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (stored_cards): {e}")
                raise

    async def delete_card(self, card_id, gateway_buyer_uuid):
        """Delete Stored Card - DELETE /v1/checkout/delete-card"""
        endpoint = f"{self.base_url}/checkout/delete-card"
        params = {"id": card_id, "gateway_buyer_uuid": gateway_buyer_uuid}
        signed_fields = ["id", "gateway_buyer_uuid"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (delete_card): {e}")
                raise

    async def card_payment(self, payload):
        """Card Payment - POST /v1/checkout/card-payment"""
        endpoint = f"{self.base_url}/checkout/card-payment"
        signed_fields = ["transid", "vendor", "order_id", "card_token", "buyer_userid", "gateway_buyer_uuid"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (card_payment): {e}")
                raise

    async def wallet_payment(self, transid, order_id, msisdn):
        """Wallet Payment - POST /v1/checkout/wallet-payment"""
        endpoint = f"{self.base_url}/checkout/wallet-payment"
        payload = {"transid": transid, "order_id": order_id, "msisdn": msisdn}
        signed_fields = ["transid", "order_id", "msisdn"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (wallet_payment): {e}")
                raise

    async def selcompesa_payment(self, transid, order_id, msisdn, remarks=None):
        """Selcom Pesa Payment - POST /v1/checkout/selcompesa-payment"""
        endpoint = f"{self.base_url}/checkout/selcompesa-payment"
        payload = {"transid": transid, "order_id": order_id, "msisdn": msisdn}
        if remarks:
            payload["remarks"] = remarks
        signed_fields = ["transid", "order_id", "msisdn"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (selcompesa_payment): {e}")
                raise

    async def create_till_alias(self, name, memo):
        """Create Till Alias - POST /v1/checkout/create-till-alias"""
        endpoint = f"{self.base_url}/checkout/create-till-alias"
        payload = {"vendor": self.vendor_id, "name": name, "memo": memo}
        signed_fields = ["vendor", "name", "memo"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (create_till_alias): {e}")
                raise

    # ==================== C2B / Wallet Pull ====================

    async def wallet_push_ussd(self, transid, utilityref, amount, msisdn):
        """Wallet Pull Funds (Push USSD) - POST /v1/wallet/pushussd"""
        endpoint = f"{self.base_url}/wallet/pushussd"
        payload = {
            "transid": transid,
            "utilityref": utilityref,
            "amount": str(amount),
            "vendor": self.vendor_id,
            "msisdn": msisdn,
        }
        signed_fields = ["transid", "utilityref", "amount", "vendor", "msisdn"]
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (wallet_push_ussd): {e}")
                raise

    async def c2b_query_status(self, transid=None, reference=None):
        """C2B Query Status - GET /v1/c2b/query-status"""
        endpoint = f"{self.base_url}/c2b/query-status"
        params = {}
        if transid:
            params["transid"] = transid
        if reference:
            params["reference"] = reference
        signed_fields = [k for k in params.keys()]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (c2b_query_status): {e}")
                raise

    # ==================== POS ====================

    async def initiate_pos_payment(self, currency, amount, payment_method=None, msisdn=None, invoice_no=None):
        """Initiate POS Payment - POST /v1/checkout/initiate-pos-payment"""
        endpoint = f"{self.base_url}/checkout/initiate-pos-payment"
        payload = {"currency": currency, "amount": str(amount)}
        if payment_method:
            payload["payment_method"] = payment_method
        if msisdn:
            payload["msisdn"] = msisdn
        if invoice_no:
            payload["invoice_no"] = invoice_no
        signed_fields = ["currency", "amount"]
        if payment_method:
            signed_fields.append("payment_method")
        if msisdn:
            signed_fields.append("msisdn")
        headers = self._get_headers(payload, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (initiate_pos_payment): {e}")
                raise

    async def pos_payment_status(self, invoice_no):
        """POS Payment Status - GET /v1/checkout/pos-payment-status"""
        endpoint = f"{self.base_url}/checkout/pos-payment-status"
        params = {"invoice_no": invoice_no}
        signed_fields = ["invoice_no"]
        headers = self._get_headers(params, signed_fields)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Selcom API Error (pos_payment_status): {e}")
                raise
