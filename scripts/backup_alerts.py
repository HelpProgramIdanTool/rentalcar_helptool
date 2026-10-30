"""Backup-only SMTP alerts, isolated from customer email settings."""
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import json
from pathlib import Path
import smtplib
import ssl
from zoneinfo import ZoneInfo

CONFIG = Path('/etc/secrets/backup-alerts.json')
STATE = Path('/var/data/backup-private/alert-status.json')
BACKUP_STATUS = Path('/var/data/backup-private/status.json')


def should_notify(event, state, now):
    if event == 'test':
        return True
    if event == 'recovery':
        return bool(state.get('outage_notified'))
    last = state.get('last_failure_sent')
    return not last or now - datetime.fromisoformat(last) >= timedelta(hours=6)


def build_message(config, event, now, last_success=None):
    subject = {
        'failure': 'RentalCar: резервная копия НЕ создана',
        'recovery': 'RentalCar: резервное копирование восстановлено',
        'test': 'RentalCar: проверка уведомлений о резервных копиях',
    }[event]
    message = EmailMessage()
    message['From'] = config['sender']
    message['To'] = config['recipient']
    message['Subject'] = subject
    lines = [subject, '', 'Время в Польше: ' + now.astimezone(ZoneInfo('Europe/Warsaw')).strftime('%d.%m.%Y %H:%M')]
    if event == 'failure':
        lines += ['Автоматическая попытка завершилась ошибкой.',
                  'Повтор запланирован через час, пока сервис работает.',
                  'Откройте Render → rentalcar-helptool → Logs.']
    elif event == 'recovery':
        lines += ['Новая зашифрованная копия создана и проверена обратным чтением.']
    else:
        lines += ['Это тест доставки. Сбой резервного копирования не имитировался.']
    if last_success:
        try:
            time = datetime.fromisoformat(last_success).astimezone(ZoneInfo('Europe/Warsaw'))
            lines.append('Последняя успешная копия: ' + time.strftime('%d.%m.%Y %H:%M'))
        except (ValueError, TypeError):
            pass
    lines += ['', 'Письмо не содержит клиентских данных, паролей или содержимого журналов.',
              'Уведомления отправляет работающий процесс копирования. Полная остановка Render требует отдельного внешнего мониторинга.']
    message.set_content('\n'.join(lines))
    return message


def notify(event):
    """Never mask a backup result if SMTP itself fails."""
    try:
        if not CONFIG.is_file():
            print('BACKUP ALERT NOT SENT: missing backup-alerts.json secret file.', flush=True)
            return False
        config = json.loads(CONFIG.read_text())
        state = json.loads(STATE.read_text()) if STATE.exists() else {}
        now = datetime.now(timezone.utc)
        if not should_notify(event, state, now):
            return True
        status = json.loads(BACKUP_STATUS.read_text()) if BACKUP_STATUS.exists() else {}
        message = build_message(config, event, now, status.get('last_success'))
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as connection:
            connection.ehlo()
            connection.starttls(context=ssl.create_default_context())
            connection.ehlo()
            connection.login(config['sender'], config['password'].replace(' ', ''))
            refused = connection.send_message(message)
            if refused:
                raise RuntimeError('Recipient refused')
        if event == 'test':
            print('BACKUP ALERT TEST SENT. Confirm receipt in the mailbox.', flush=True)
            return True
        if event == 'failure':
            state.update(last_failure_sent=now.isoformat(), outage_notified=True)
        else:
            state['outage_notified'] = False
            state.pop('last_failure_sent', None)
        STATE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = STATE.with_suffix('.new')
        temporary.write_text(json.dumps(state), encoding='utf-8')
        temporary.chmod(0o600)
        temporary.replace(STATE)
        print('BACKUP ALERT SENT: ' + event, flush=True)
        return True
    except Exception as error:
        print('BACKUP ALERT DELIVERY FAILED (' + type(error).__name__ + '). Check alert settings; no secrets logged.', flush=True)
        return False


if __name__ == '__main__':
    raise SystemExit(0 if notify('test') else 1)
