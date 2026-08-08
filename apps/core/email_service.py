import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


def send_welcome_email(email, full_name, phone_number):
    """
    Send welcome email after registration.
    """
    if not email:
        return False

    subject = "Karibu SalamaPay! Your account has been created"

    message = f"""Karibu {full_name}!

Your SalamaPay account has been created successfully.

Account Details:
  Phone: {phone_number}
  Name: {full_name}

Next Steps:
  1. Verify your phone number using the OTP code sent to your phone.
  2. Login to your account.
  3. Create your first business.
  4. Complete KYC verification to start accepting payments.

If you have any questions, contact us at {settings.ADMIN_EMAIL}

SalamaPay Team
Copyright (c) 2026 SalamaPay. All rights reserved.
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
        logger.info(f"Welcome email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {str(e)}")
        return False


def send_otp_email(email, otp_code, full_name):
    """
    Send OTP code via email.
    """
    if not email:
        return False

    subject = "SalamaPay - Your Verification Code"

    message = f"""Hello {full_name},

Your SalamaPay verification code is: {otp_code}

This code will expire in 10 minutes.

Do not share this code with anyone.

If you did not request this code, please ignore this email.

SalamaPay Team
Copyright (c) 2026 SalamaPay. All rights reserved.
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
        logger.info(f"OTP email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False


def send_password_reset_email(email, full_name):
    """
    Send password reset notification via email.
    """
    if not email:
        return False

    subject = "SalamaPay - Password Reset Request"

    message = f"""Hello {full_name},

We received a request to reset your SalamaPay account password.

Your password can now be reset from the SalamaPay app.

If you did not request a password reset, please ignore this email or contact support.

SalamaPay Team
Copyright (c) 2026 SalamaPay. All rights reserved.
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
        logger.info(f"Password reset email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        return False
