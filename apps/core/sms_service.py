import httpx
import logging
from django.conf import settings
from .models import SMSLog

logger = logging.getLogger(__name__)


class SMSService:
    """
    SMS service using messaging-service.co.tz gateway.
    """

    BASE_URL = "https://messaging-service.co.tz/api/sms/v1/text/single"

    def __init__(self):
        self.auth_token = getattr(settings, 'SMS_AUTH_TOKEN', 'Basic ZWxhbmJyYW5kczpFbGl5YWFtb3MxQA==')
        self.sender_id = getattr(settings, 'SMS_SENDER_ID', 'Elan Brands')

    def send_sms(self, phone, text):
        """
        Send SMS to a single phone number.
        Returns (success: bool, response: dict)
        """
        log = SMSLog.objects.create(
            phone=phone,
            message=text,
            status='PENDING'
        )

        try:
            payload = {
                "from": self.sender_id,
                "to": [phone],
                "text": text
            }

            headers = {
                "Authorization": self.auth_token,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            with httpx.Client(timeout=30) as client:
                response = client.post(
                    self.BASE_URL,
                    json=payload,
                    headers=headers
                )

            res_data = response.json()

            try:
                group_name = res_data['messages'][0]['status']['groupName']
            except (KeyError, IndexError, TypeError):
                group_name = 'UNKNOWN'

            if group_name == "PENDING":
                log.status = 'SENT'
                log.response = str(res_data)
                log.save()
                logger.info(f"SMS sent to {phone}: {text[:50]}...")
                return True, res_data
            else:
                log.status = 'FAILED'
                log.response = str(res_data)
                log.save()
                logger.error(f"SMS failed to {phone}: {group_name}")
                return False, res_data

        except httpx.TimeoutException:
            log.status = 'FAILED'
            log.response = 'Timeout'
            log.save()
            logger.error(f"SMS timeout to {phone}")
            return False, {"error": "Timeout"}

        except Exception as e:
            log.status = 'FAILED'
            log.response = str(e)
            log.save()
            logger.error(f"SMS error to {phone}: {str(e)}")
            return False, {"error": str(e)}


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
