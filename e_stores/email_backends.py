import logging
import requests

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class BrevoEmailBackend(BaseEmailBackend):
    """Send email through Brevo (formerly Sendinblue) HTTP API."""

    API_URL = 'https://api.brevo.com/v3/smtp/email'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = getattr(settings, 'BREVO_API_KEY', '')
        self.sender_email = getattr(settings, 'BREVO_SENDER_EMAIL', '')
        self.sender_name = getattr(settings, 'BREVO_SENDER_NAME', 'Olid Stores')
        self.timeout = getattr(settings, 'EMAIL_SEND_TIMEOUT', 10)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            logger.error('BrevoEmailBackend: BREVO_API_KEY is not configured.')
            return 0

        sent_count = 0
        for message in email_messages:
            if self._send_email_message(message):
                sent_count += 1

        return sent_count

    def _send_email_message(self, message):
        recipients = [{'email': recipient} for recipient in message.to or []]
        if not recipients:
            logger.warning('BrevoEmailBackend: no recipients provided. Skipping email.')
            return False

        html_content = None
        if getattr(message, 'alternatives', None):
            for alternative, mime in message.alternatives:
                if mime == 'text/html':
                    html_content = alternative
                    break

        payload = {
            'sender': {'name': self.sender_name, 'email': self.sender_email},
            'to': recipients,
            'subject': message.subject,
            'textContent': message.body,
        }

        if html_content:
            payload['htmlContent'] = html_content

        if message.cc:
            payload['cc'] = [{'email': recipient} for recipient in message.cc]
        if message.bcc:
            payload['bcc'] = [{'email': recipient} for recipient in message.bcc]

        if message.extra_headers:
            reply_to = message.extra_headers.get('Reply-To')
            if reply_to:
                payload['replyTo'] = {'email': reply_to}

        headers = {
            'api-key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        try:
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            logger.error('BrevoEmailBackend: failed to send email: %s', exc)
            if not self.fail_silently:
                raise
            return False


class ResendEmailBackend(BaseEmailBackend):
    """Send email through Resend HTTP API."""

    API_URL = 'https://api.resend.com/emails'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = getattr(settings, 'RESEND_API_KEY', '')
        self.sender_email = getattr(settings, 'RESEND_SENDER_EMAIL', '')
        self.sender_name = getattr(settings, 'RESEND_SENDER_NAME', 'Olid Stores')
        self.timeout = getattr(settings, 'EMAIL_SEND_TIMEOUT', 10)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            logger.error('ResendEmailBackend: RESEND_API_KEY is not configured.')
            return 0

        sent_count = 0
        for message in email_messages:
            if self._send_email_message(message):
                sent_count += 1

        return sent_count

    def _send_email_message(self, message):
        recipients = [{'email': recipient} for recipient in message.to or []]
        if not recipients:
            logger.warning('ResendEmailBackend: no recipients provided. Skipping email.')
            return False

        html_content = None
        if getattr(message, 'alternatives', None):
            for alternative, mime in message.alternatives:
                if mime == 'text/html':
                    html_content = alternative
                    break

        payload = {
            'from': f'{self.sender_name} <{self.sender_email}>',
            'to': recipients,
            'subject': message.subject,
            'text': message.body,
        }

        if html_content:
            payload['html'] = html_content
        else:
            payload['html'] = message.body

        if message.extra_headers:
            reply_to = message.extra_headers.get('Reply-To')
            if reply_to:
                payload['reply_to'] = reply_to

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            logger.error('ResendEmailBackend: failed to send email: %s', exc)
            if not self.fail_silently:
                raise
            return False
