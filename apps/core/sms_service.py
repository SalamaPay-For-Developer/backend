import httpx
import logging
from django.conf import settings
from .models import SMSLog

logger = logging.getLogger(__name__)

# V1 API for sending SMS (uses Basic Auth)
SMS_SEND_URL = "https://messaging-service.co.tz/api/sms/v1/text/single"

# V2 API for balance and logs (uses Bearer Token)
SMS_V2_BASE = "https://messaging-service.co.tz/api/v2"
SMS_LOGS_URL = f"{SMS_V2_BASE}/logs"
SMS_BALANCE_URL = f"{SMS_V2_BASE}/balance"


class SMSService:
    """
    SMS service using messaging-service.co.tz.
    - Sending SMS: V1 API with Basic Auth
    - Balance/Logs: V2 API with Bearer Token
    """

    def __init__(self):
        self.basic_auth = getattr(settings, 'SMS_BASIC_AUTH', 'Basic ZWxhbmJyYW5kczpFbGl5YWFtb3MxQA==')
        self.bearer_token = getattr(settings, 'SMS_BEARER_TOKEN', '947e205d5e067b669f3a9caa0087277f')
        self.sender_id = getattr(settings, 'SMS_SENDER_ID', 'Elan Brands')

    def _get_v1_headers(self):
        return {
            "Authorization": self.basic_auth,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _get_v2_headers(self):
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _normalize_phone(self, phone):
        """Normalize phone to 255XXXXXXXXX format (no +)."""
        phone = phone.replace("+", "").replace(" ", "")
        if phone.startswith("255"):
            return phone
        if phone.startswith("0"):
            return "255" + phone[1:]
        return phone

    def send_sms(self, phone, text):
        """
        Send SMS to a single phone number using V1 API.
        Returns (success: bool, response: dict)
        """
        normalized_phone = self._normalize_phone(phone)

        log = SMSLog.objects.create(
            phone=phone,
            message=text,
            status='PENDING'
        )

        try:
            payload = {
                "from": self.sender_id,
                "to": [normalized_phone],
                "text": text
            }

            with httpx.Client(timeout=30) as client:
                response = client.post(
                    SMS_SEND_URL,
                    json=payload,
                    headers=self._get_v1_headers()
                )

            res_data = response.json()

            try:
                group_name = res_data['messages'][0]['status']['groupName']
            except (KeyError, IndexError, TypeError):
                group_name = 'UNKNOWN'

            if group_name in ("PENDING", "ACCEPTED", "PENDING_ENROUTE"):
                log.status = 'SENT'
                log.response = str(res_data)
                log.save()
                logger.info(f"SMS sent to {normalized_phone}: {text[:50]}...")
                return True, res_data
            else:
                log.status = 'FAILED'
                log.response = str(res_data)
                log.save()
                logger.error(f"SMS failed to {normalized_phone}: {group_name}")
                return False, res_data

        except httpx.TimeoutException:
            log.status = 'FAILED'
            log.response = 'Timeout'
            log.save()
            logger.error(f"SMS timeout to {normalized_phone}")
            return False, {"error": "Timeout"}

        except Exception as e:
            log.status = 'FAILED'
            log.response = str(e)
            log.save()
            logger.error(f"SMS error to {normalized_phone}: {str(e)}")
            return False, {"error": str(e)}

    def get_balance(self):
        """
        Get SMS balance using V2 API.
        Returns dict with balance info.
        """
        try:
            with httpx.Client(timeout=15) as client:
                response = client.get(
                    SMS_BALANCE_URL,
                    headers=self._get_v2_headers()
                )
            return response.json()
        except Exception as e:
            logger.error(f"SMS balance check failed: {str(e)}")
            return {"error": str(e)}

    def get_logs(self, phone=None, limit=50, sent_since=None, sent_until=None):
        """
        Get SMS logs using V2 API with optional filters.
        Returns dict with results.
        """
        try:
            params = {"limit": limit}
            if phone:
                params["to"] = self._normalize_phone(phone)
            if sent_since:
                params["sentSince"] = sent_since
            if sent_until:
                params["sentUntil"] = sent_until

            with httpx.Client(timeout=15) as client:
                response = client.get(
                    SMS_LOGS_URL,
                    params=params,
                    headers=self._get_v2_headers()
                )
            return response.json()
        except Exception as e:
            logger.error(f"SMS logs fetch failed: {str(e)}")
            return {"error": str(e)}


sms_service = SMSService()


def send_otp_sms(phone, otp_code):
    """
    Send OTP verification code via SMS.
    """
    message = f"SalamaPay: Your verification code is {otp_code}. Do not share this code with anyone."
    return sms_service.send_sms(phone, message)


def send_password_reset_sms(phone):
    """
    Send password reset notification via SMS.
    """
    message = f"SalamaPay: Your password reset request has been received. Use the app to set a new password."
    return sms_service.send_sms(phone, message)


def send_welcome_sms(phone, full_name):
    """
    Send welcome SMS after registration.
    """
    message = f"SalamaPay: Karibu {full_name}! Your account has been created. Verify your phone to get started."
    return sms_service.send_sms(phone, message)
