"""Server work mail: test recipient only until explicitly enabled at cutover."""
from email.utils import getaddresses
import json
from pathlib import Path
from smtplib import SMTPException

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend

CONFIG = Path('/etc/secrets/work-mail.json')


class WorkMailBlocked(SMTPException):
    pass


def load_work_mail():
    if not CONFIG.is_file():
        return {}
    return json.loads(CONFIG.read_text(encoding='utf-8-sig'))


def mailbox(value):
    if '\r' in value or '\n' in value:
        raise WorkMailBlocked('Некорректный адрес электронной почты.')
    parsed = getaddresses([value])
    if len(parsed) != 1 or not parsed[0][1] or '@' not in parsed[0][1]:
        raise WorkMailBlocked('Некорректный адрес электронной почты.')
    return parsed[0][1].casefold()


class GuardedWorkMailBackend(EmailBackend):
    def __init__(self, **kwargs):
        try:
            self.config = load_work_mail()
        except (OSError, ValueError):
            raise WorkMailBlocked('Не удалось прочитать настройки почты сервера.') from None
        super().__init__(host='smtp.gmail.com', port=587, use_tls=True, use_ssl=False,
                         ssl_keyfile='', ssl_certfile='',
                         username=self.config.get('sender', ''),
                         password=self.config.get('password', '').replace(' ', ''),
                         timeout=30, **kwargs)

    def send_messages(self, email_messages):
        messages = list(email_messages or [])
        if not messages:
            return 0
        mode = getattr(settings, 'WORK_MAIL_MODE', 'test-only')
        if mode not in ('test-only', 'live'):
            raise WorkMailBlocked('Отправка рабочих писем с сервера отключена.')
        if not all(self.config.get(key) for key in ('sender', 'password', 'test_recipient')):
            raise WorkMailBlocked('Почта сервера ещё не настроена. Работайте в локальной программе.')
        sender = mailbox(self.config['sender'])
        allowed = mailbox(self.config['test_recipient'])
        # Validate the whole batch before any SMTP connection or partial send.
        for message in messages:
            if mailbox(message.from_email) != sender:
                raise WorkMailBlocked('Адрес отправителя не совпадает с настройками почты сервера.')
            recipients = [mailbox(address) for address in message.recipients()]
            if not recipients:
                raise WorkMailBlocked('Не указан получатель письма.')
            if mode == 'test-only' and any(address != allowed for address in recipients):
                raise WorkMailBlocked('Сервер в тестовом режиме: письма клиентам и поставщикам заблокированы. Разрешён только проверочный адрес администратора. Работайте локально.')
        return super().send_messages(messages)
