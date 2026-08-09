import uuid
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from asgiref.sync import async_to_sync
from apps.selcom.client import SelcomClient


class WalletNameLookupView(APIView):
    """
    IMT Wallet Name Lookup via Selcom.
    POST /api/v1/imt/wallet-name-lookup/
    Body: { "phone_number": "2557XXXXXXXX", "utilitycode": "MPREMITIN" }
    """
    permission_classes = [IsAuthenticated]

    UTILITY_CODES = {
        "MPESA": "MPREMITIN",
        "MIXX BY YAS": "TPREMITIN",
        "HALOPESA": "HPREMITIN",
        "AIRTELMONEY": "AMREMITIN",
        "TTCL PESA": "TTREMITIN",
    }

    def post(self, request):
        phone_number = request.data.get('phone_number')
        utilitycode = request.data.get('utilitycode', 'MPREMITIN')

        if not phone_number:
            return Response(
                {"detail": "Phone number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        normalized = phone_number.strip()
        if normalized.startswith('+'):
            normalized = normalized[1:]
        elif normalized.startswith('0'):
            normalized = '255' + normalized[1:]
        elif not normalized.startswith('255'):
            normalized = '255' + normalized

        transid = f"SP-LK-{uuid.uuid4().hex[:10].upper()}"

        client = SelcomClient()
        try:
            result = async_to_sync(client.wallet_name_lookup)(
                utilitycode=utilitycode,
                utilityref=normalized,
                transid=transid
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": "Name lookup failed", "error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )


class BankNameLookupView(APIView):
    """
    IMT Bank Account Name Lookup via Selcom.
    POST /api/v1/imt/bank-name-lookup/
    Body: { "bank": "AKIBA", "account": "000000040000" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        bank = request.data.get('bank')
        account = request.data.get('account')

        if not bank or not account:
            return Response(
                {"detail": "Bank and account are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        transid = f"SP-BL-{uuid.uuid4().hex[:10].upper()}"

        client = SelcomClient()
        try:
            result = async_to_sync(client.bank_name_lookup)(
                bank=bank,
                account=account,
                transid=transid
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": "Bank name lookup failed", "error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )


class SendMoneyView(APIView):
    """
    IMT Send Money via Selcom.
    POST /api/v1/imt/send-money/
    Body: full Selcom send-money payload
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = request.data.copy()

        if not payload.get('messageId'):
            payload['messageId'] = f"SP-SM-{uuid.uuid4().hex[:10].upper()}"
        if not payload.get('end2endId'):
            payload['end2endId'] = payload['messageId']
        if not payload.get('vendor'):
            from django.conf import settings
            payload['vendor'] = settings.SELCOM_VENDOR_ID

        client = SelcomClient()
        try:
            result = async_to_sync(client.send_money)(payload)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": "Send money failed", "error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )


class IMTTransactionStatusView(APIView):
    """
    IMT Transaction Status via Selcom.
    GET /api/v1/imt/transaction-status/?messageId=XXXX
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        message_id = request.query_params.get('messageId')
        if not message_id:
            return Response(
                {"detail": "messageId is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        client = SelcomClient()
        try:
            result = async_to_sync(client.imt_transaction_status)(message_id)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": "Status query failed", "error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )


# ==================== Utility Payments ====================

class UtilityPaymentView(APIView):
    """POST /api/v1/utility-payment/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        required = ['utilitycode', 'utilityref', 'amount', 'pin']
        for field in required:
            if not data.get(field):
                return Response({"detail": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-UP-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.utility_payment)(
                transid=transid,
                utilitycode=data['utilitycode'],
                utilityref=data['utilityref'],
                amount=data['amount'],
                pin=data['pin'],
                msisdn=data.get('msisdn'),
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Utility payment failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class UtilityLookupView(APIView):
    """POST /api/v1/utility-lookup/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not data.get('utilitycode') or not data.get('utilityref'):
            return Response({"detail": "utilitycode and utilityref are required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-UL-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.utility_lookup)(
                utilitycode=data['utilitycode'],
                utilityref=data['utilityref'],
                transid=transid,
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Utility lookup failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class UtilityPaymentStatusView(APIView):
    """GET /api/v1/utility-payment/status/?transid=XXXX"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transid = request.query_params.get('transid')
        if not transid:
            return Response({"detail": "transid is required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.utility_payment_status)(transid)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Status query failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


# ==================== Wallet Cashin ====================

class WalletCashinView(APIView):
    """POST /api/v1/wallet-cashin/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        required = ['utilitycode', 'utilityref', 'amount', 'pin']
        for field in required:
            if not data.get(field):
                return Response({"detail": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-WC-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.wallet_cashin)(
                transid=transid,
                utilitycode=data['utilitycode'],
                utilityref=data['utilityref'],
                amount=data['amount'],
                pin=data['pin'],
                msisdn=data.get('msisdn'),
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Wallet cashin failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class WalletCashinLookupView(APIView):
    """POST /api/v1/wallet-cashin/lookup/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not data.get('utilitycode') or not data.get('utilityref'):
            return Response({"detail": "utilitycode and utilityref are required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-WL-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.wallet_cashin_name_lookup)(
                utilitycode=data['utilitycode'],
                utilityref=data['utilityref'],
                transid=transid,
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Wallet cashin lookup failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class WalletCashinStatusView(APIView):
    """GET /api/v1/wallet-cashin/status/?transid=XXXX"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transid = request.query_params.get('transid')
        if not transid:
            return Response({"detail": "transid is required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.wallet_cashin_status)(transid)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Status query failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


# ==================== Selcom Pesa ====================

class SelcomPesaCashinView(APIView):
    """POST /api/v1/selcompesa/cashin/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        required = ['utilityref', 'amount', 'pin']
        for field in required:
            if not data.get(field):
                return Response({"detail": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-SP-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.selcompesa_cashin)(
                transid=transid,
                utilityref=data['utilityref'],
                amount=data['amount'],
                pin=data['pin'],
                msisdn=data.get('msisdn'),
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Selcom Pesa cashin failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class SelcomPesaLookupView(APIView):
    """POST /api/v1/selcompesa/lookup/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not data.get('utilityref'):
            return Response({"detail": "utilityref is required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-SL-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.selcompesa_name_lookup)(
                utilityref=data['utilityref'],
                transid=transid,
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Selcom Pesa lookup failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class SelcomPesaStatusView(APIView):
    """GET /api/v1/selcompesa/status/?transid=XXXX"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transid = request.query_params.get('transid')
        if not transid:
            return Response({"detail": "transid is required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.selcompesa_status)(transid)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Status query failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


# ==================== Agent Cashout ====================

class AgentCashoutView(APIView):
    """POST /api/v1/agent-cashout/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        required = ['utilityref', 'amount', 'pin']
        for field in required:
            if not data.get(field):
                return Response({"detail": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-AC-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.agent_cashout)(
                transid=transid,
                utilityref=data['utilityref'],
                amount=data['amount'],
                pin=data['pin'],
                name=data.get('name'),
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Agent cashout failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class AgentCashoutStatusView(APIView):
    """GET /api/v1/agent-cashout/status/?transid=XXXX"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transid = request.query_params.get('transid')
        if not transid:
            return Response({"detail": "transid is required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.agent_cashout_status)(transid)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Status query failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


# ==================== Float Account ====================

class FloatBalanceView(APIView):
    """POST /api/v1/float/balance/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not data.get('pin'):
            return Response({"detail": "pin is required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-FB-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.float_balance)(pin=data['pin'], transid=transid)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Balance query failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


# ==================== Qwiksend (Bank Transfer) ====================

class QwiksendProcessView(APIView):
    """POST /api/v1/qwiksend/process/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        required = ['recipientFiCode', 'recipientAccount', 'recipientName', 'senderAccount', 'senderName', 'amount', 'pin', 'msisdn', 'purpose']
        for field in required:
            if not data.get(field):
                return Response({"detail": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        data.setdefault('transid', f"SP-QS-{uuid.uuid4().hex[:10].upper()}")
        data.setdefault('vendor', SelcomClient().vendor_id)
        client = SelcomClient()
        try:
            result = async_to_sync(client.qwiksend_process)(data)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Qwiksend failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class QwiksendLookupView(APIView):
    """POST /api/v1/qwiksend/lookup/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not data.get('bank') or not data.get('account'):
            return Response({"detail": "bank and account are required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-QL-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.qwiksend_lookup)(
                bank=data['bank'], account=data['account'], transid=transid,
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Qwiksend lookup failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class QwiksendStatusView(APIView):
    """GET /api/v1/qwiksend/status/?transid=XXXX"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transid = request.query_params.get('transid')
        if not transid:
            return Response({"detail": "transid is required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.qwiksend_status)(transid)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Status query failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


# ==================== VCN ====================

class VCNCreateView(APIView):
    """POST /api/v1/vcn/create/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data.setdefault('transid', f"SP-VC-{uuid.uuid4().hex[:10].upper()}")
        data.setdefault('vendor', SelcomClient().vendor_id)
        client = SelcomClient()
        try:
            result = async_to_sync(client.vcn_create)(data)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "VCN creation failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class VCNCreateStatusView(APIView):
    """GET /api/v1/vcn/create-status/?msisdn=XXX&transid=XXX"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        msisdn = request.query_params.get('msisdn')
        transid = request.query_params.get('transid')
        if not msisdn or not transid:
            return Response({"detail": "msisdn and transid are required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.vcn_create_status)(msisdn, transid)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "VCN status query failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class VCNChangeStatusView(APIView):
    """POST /api/v1/vcn/change-status/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data.setdefault('requestid', f"SP-VS-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.vcn_change_status)(data)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "VCN status change failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class VCNShowView(APIView):
    """POST /api/v1/vcn/show/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data.setdefault('requestid', f"SP-VH-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.vcn_show)(data)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "VCN show failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class VCNStatusView(APIView):
    """GET /api/v1/vcn/status/?msisdn=XXX&account=XXX"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        msisdn = request.query_params.get('msisdn')
        account = request.query_params.get('account')
        if not msisdn or not account:
            return Response({"detail": "msisdn and account are required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.vcn_status)(msisdn, account)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "VCN status failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class VCNSetLimitView(APIView):
    """POST /api/v1/vcn/set-limit/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        client = SelcomClient()
        try:
            result = async_to_sync(client.vcn_set_limit)(data)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "VCN set limit failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


# ==================== Checkout ====================

class CreateOrderMinimalView(APIView):
    """POST /api/v1/checkout/create-order-minimal/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data.setdefault('vendor', SelcomClient().vendor_id)
        client = SelcomClient()
        try:
            result = async_to_sync(client.create_order_minimal)(data)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Create order failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class CancelOrderView(APIView):
    """DELETE /api/v1/checkout/cancel-order/?order_id=XXX"""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        order_id = request.query_params.get('order_id')
        if not order_id:
            return Response({"detail": "order_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.cancel_order)(order_id)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Cancel order failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class ListOrdersView(APIView):
    """GET /api/v1/checkout/list-orders/?fromdate=YYYY-MM-DD&todate=YYYY-MM-DD"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        fromdate = request.query_params.get('fromdate')
        todate = request.query_params.get('todate')
        if not fromdate or not todate:
            return Response({"detail": "fromdate and todate are required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.list_orders)(fromdate, todate)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "List orders failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class StoredCardsView(APIView):
    """GET /api/v1/checkout/stored-cards/?buyer_userid=XXX&gateway_buyer_uuid=XXX"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        buyer_userid = request.query_params.get('buyer_userid')
        gateway_buyer_uuid = request.query_params.get('gateway_buyer_uuid')
        if not buyer_userid or not gateway_buyer_uuid:
            return Response({"detail": "buyer_userid and gateway_buyer_uuid are required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.stored_cards)(buyer_userid, gateway_buyer_uuid)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Stored cards fetch failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class DeleteCardView(APIView):
    """DELETE /api/v1/checkout/delete-card/?id=XXX&gateway_buyer_uuid=XXX"""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        card_id = request.query_params.get('id')
        gateway_buyer_uuid = request.query_params.get('gateway_buyer_uuid')
        if not card_id or not gateway_buyer_uuid:
            return Response({"detail": "id and gateway_buyer_uuid are required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.delete_card)(card_id, gateway_buyer_uuid)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Delete card failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class CardPaymentView(APIView):
    """POST /api/v1/checkout/card-payment/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data.setdefault('transid', f"SP-CP-{uuid.uuid4().hex[:10].upper()}")
        data.setdefault('vendor', SelcomClient().vendor_id)
        client = SelcomClient()
        try:
            result = async_to_sync(client.card_payment)(data)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Card payment failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class WalletPaymentView(APIView):
    """POST /api/v1/checkout/wallet-payment/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        required = ['order_id', 'msisdn']
        for field in required:
            if not data.get(field):
                return Response({"detail": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-WP-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.wallet_payment)(transid, data['order_id'], data['msisdn'])
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Wallet payment failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class SelcomPesaPaymentView(APIView):
    """POST /api/v1/checkout/selcompesa-payment/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        required = ['order_id', 'msisdn']
        for field in required:
            if not data.get(field):
                return Response({"detail": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-SPP-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.selcompesa_payment)(transid, data['order_id'], data['msisdn'], data.get('remarks'))
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Selcom Pesa payment failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class CreateTillAliasView(APIView):
    """POST /api/v1/checkout/create-till-alias/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not data.get('name') or not data.get('memo'):
            return Response({"detail": "name and memo are required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.create_till_alias)(data['name'], data['memo'])
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Create till alias failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


# ==================== C2B / Wallet Pull ====================

class WalletPushUssdView(APIView):
    """POST /api/v1/wallet/push-ussd/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        required = ['utilityref', 'amount', 'msisdn']
        for field in required:
            if not data.get(field):
                return Response({"detail": f"{field} is required."}, status=status.HTTP_400_BAD_REQUEST)

        transid = data.get('transid', f"SP-WU-{uuid.uuid4().hex[:10].upper()}")
        client = SelcomClient()
        try:
            result = async_to_sync(client.wallet_push_ussd)(
                transid=transid,
                utilityref=data['utilityref'],
                amount=data['amount'],
                msisdn=data['msisdn'],
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Wallet push USSD failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class C2BQueryStatusView(APIView):
    """GET /api/v1/c2b/query-status/?transid=XXX or ?reference=XXX"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transid = request.query_params.get('transid')
        reference = request.query_params.get('reference')
        if not transid and not reference:
            return Response({"detail": "transid or reference is required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.c2b_query_status)(transid=transid, reference=reference)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "C2B status query failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


# ==================== POS ====================

class InitiatePosPaymentView(APIView):
    """POST /api/v1/pos/initiate/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not data.get('currency') or not data.get('amount'):
            return Response({"detail": "currency and amount are required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.initiate_pos_payment)(
                currency=data['currency'],
                amount=data['amount'],
                payment_method=data.get('payment_method'),
                msisdn=data.get('msisdn'),
                invoice_no=data.get('invoice_no'),
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "POS payment initiation failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class PosPaymentStatusView(APIView):
    """GET /api/v1/pos/status/?invoice_no=XXX"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invoice_no = request.query_params.get('invoice_no')
        if not invoice_no:
            return Response({"detail": "invoice_no is required."}, status=status.HTTP_400_BAD_REQUEST)

        client = SelcomClient()
        try:
            result = async_to_sync(client.pos_payment_status)(invoice_no)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "POS status query failed", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
