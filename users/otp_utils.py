"""
OTP Utility Functions for Email and SMS Verification
"""
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)


def send_email_otp(email, otp_code, purpose='verification'):
    """
    Send OTP code via email.
    
    Args:
        email: Recipient email address
        otp_code: The 6-digit OTP code
        purpose: 'verification' or 'login'
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    subject = f'Your E-Stores Verification Code: {otp_code}'
    
    message = f"""
Hello,

Your verification code is: {otp_code}

This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.

If you did not request this code, please ignore this email.

Best regards,
E-Stores Team
"""
    
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #1a56db, #0e3a9b); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
        .otp-code {{ font-size: 32px; font-weight: bold; color: #1a56db; letter-spacing: 8px; text-align: center; padding: 20px; background: white; border-radius: 8px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">E-Stores</h1>
            <p style="margin: 5px 0 0;">Email Verification</p>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>Your verification code is:</p>
            <div class="otp-code">{otp_code}</div>
            <p>This code will expire in <strong>{settings.OTP_EXPIRY_MINUTES} minutes</strong>.</p>
            <p>If you did not request this code, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>&copy; E-Stores. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    try:
        if getattr(settings, 'OTP_DEBUG_MODE', False):
            logger.info(f"[DEBUG] Email OTP for {email}: {otp_code}")
            print(f"\n{'='*50}")
            print(f"EMAIL OTP DEBUG")
            print(f"To: {email}")
            print(f"Code: {otp_code}")
            print(f"{'='*50}\n")
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send email OTP to {email}: {e}")
        return False


def send_sms_otp(phone, otp_code):
    """
    Send OTP code via SMS using Twilio.
    
    Args:
        phone: Recipient phone number (with country code, e.g., +2348012345678)
        otp_code: The 6-digit OTP code
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    # Debug mode - just print to console
    if getattr(settings, 'OTP_DEBUG_MODE', False):
        logger.info(f"[DEBUG] SMS OTP for {phone}: {otp_code}")
        print(f"\n{'='*50}")
        print(f"SMS OTP DEBUG")
        print(f"To: {phone}")
        print(f"Code: {otp_code}")
        print(f"{'='*50}\n")
        return True
    
    # Check Twilio credentials
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
    
    if not all([account_sid, auth_token, from_number]):
        logger.error("Twilio credentials not configured")
        return False
    
    try:
        from twilio.rest import Client
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=f"Your E-Stores verification code is: {otp_code}. Valid for {settings.OTP_EXPIRY_MINUTES} minutes.",
            from_=from_number,
            to=phone
        )
        
        logger.info(f"SMS sent to {phone}, SID: {message.sid}")
        return True
        
    except ImportError:
        logger.error("Twilio package not installed. Run: pip install twilio")
        return False
    except Exception as e:
        logger.error(f"Failed to send SMS OTP to {phone}: {e}")
        return False


def normalize_phone_number(phone):
    """
    Normalize phone number to international format.
    Assumes Nigerian numbers if no country code provided.
    
    Examples:
        08012345678 -> +2348012345678
        +2348012345678 -> +2348012345678
        2348012345678 -> +2348012345678
    """
    if not phone:
        return ''
    
    # Remove spaces, dashes, parentheses
    phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # If already has + prefix, return as is
    if phone.startswith('+'):
        return phone
    
    # Nigerian number starting with 0
    if phone.startswith('0') and len(phone) == 11:
        return '+234' + phone[1:]
    
    # Nigerian number starting with 234
    if phone.startswith('234') and len(phone) == 13:
        return '+' + phone
    
    # Assume it needs Nigerian country code
    if len(phone) == 10:
        return '+234' + phone
    
    # Return with + prefix
    return '+' + phone if not phone.startswith('+') else phone
