import logging
import requests

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class SendGridEmailBackend(BaseEmailBackend):
    """Send email through SendGrid HTTP API."""

    API_URL = 'https://api.sendgrid.com/v3/mail/send'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = getattr(settings, 'SENDGRID_API_KEY', '')
        self.sender_email = getattr(settings, 'SENDGRID_SENDER_EMAIL', '')
        self.sender_name = getattr(settings, 'SENDGRID_SENDER_NAME', 'E-Stores')
        self.timeout = getattr(settings, 'EMAIL_SEND_TIMEOUT', 10)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            logger.error('SendGridEmailBackend: SENDGRID_API_KEY is not configured.')
            return 0

        sent_count = 0
        for message in email_messages:
            if self._send_email_message(message):
                sent_count += 1

        return sent_count

    def _send_email_message(self, message):
        personalizations = [{
            'to': [{'email': recipient} for recipient in message.to or []],
        }]

        if message.cc:
            personalizations[0]['cc'] = [{'email': recipient} for recipient in message.cc]
        if message.bcc:
            personalizations[0]['bcc'] = [{'email': recipient} for recipient in message.bcc]

        content = []
        if message.content_subtype == 'html':
            content.append({'type': 'text/html', 'value': message.body})
            content.append({'type': 'text/plain', 'value': message.body})
        else:
            content.append({'type': 'text/plain', 'value': message.body})

        payload = {
            'personalizations': personalizations,
            'from': {
                'email': self.sender_email,
                'name': self.sender_name,
            },
            'subject': message.subject,
            'content': content,
        }

        if message.extra_headers:
            reply_to = message.extra_headers.get('Reply-To')
            if reply_to:
                payload['reply_to'] = {'email': reply_to}

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            logger.error('SendGridEmailBackend: failed to send email: %s', exc)
            if not self.fail_silently:
                raise
            return False
