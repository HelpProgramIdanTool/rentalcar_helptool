"""Check server recipient blocking, then send an invented test email to the operator."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    if os.environ.get('DJANGO_SETTINGS_MODULE') != 'config.render_settings':
        raise SystemExit('Run only in Render Shell.')
    import django
    django.setup()
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives
    from config.work_mail import WorkMailBlocked, load_work_mail

    if settings.WORK_MAIL_MODE != 'test-only':
        raise SystemExit('Set WORK_MAIL_MODE=test-only before this test.')
    config = load_work_mail()
    if not config.get('test_recipient'):
        raise SystemExit('Add work-mail.json in Render Secret Files first.')
    try:
        EmailMultiAlternatives(subject='Must be blocked', body='Invented safety test.', to=['must-not-send@example.invalid']).send()
    except WorkMailBlocked:
        print('WORK MAIL SAFETY: external recipient blocked before SMTP.', flush=True)
    else:
        raise SystemExit('WORK MAIL SAFETY FAILED; test stopped.')
    message = EmailMultiAlternatives(
        subject='RentalCar: проверка рабочей почты сервера',
        body='Это проверочное письмо с сервера RentalCar. Отправка клиентам и поставщикам остаётся заблокированной. До перехода продолжайте работать локально.',
        to=[config['test_recipient']],
    )
    message.attach_alternative('<p>Проверка рабочей почты сервера RentalCar.</p><p><strong>Отправка клиентам и поставщикам заблокирована.</strong> Продолжайте работать локально до согласованного перехода.</p>', 'text/html')
    if message.send() != 1:
        raise SystemExit('WORK MAIL TEST FAILED: mail server did not accept the test.')
    print('WORK MAIL TEST SENT: only to configured operator address. Confirm receipt.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('WORK MAIL TEST FAILED (' + type(error).__name__ + '). No secrets logged.', flush=True)
        raise SystemExit(1)
