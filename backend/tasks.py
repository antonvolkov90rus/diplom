from logging import getLogger
import time
from django.core.mail import EmailMultiAlternatives
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from backend.models import ConfirmEmailToken

logger = getLogger(__name__)

# Логика отправки писем в отдельную функцию
def prepare_email(title, message, recipient):
    """Формирует письмо."""
    try:
        msg = EmailMultiAlternatives(
            subject=title,
            body=message,
            from_email=settings.EMAIL_HOST_USER,
            to=[recipient]
        )
        msg.send()
        logger.info(f"Письмо успешно отправлено на {recipient}.")
    except Exception as excp:
        logger.error(f"Ошибка отправки письма на {recipient}: {excp}")
        return False
    return True

# Асинхронная задача для отправки письма
@shared_task()
def send_email(title, message, email):
    """Отправляет одно письмо асинхронно."""
    result = prepare_email(title, message, email)
    if not result:
        logger.warning(f"Неудачная попытка отправки письма на {email}.")

# Массовая отправка писем
def mass_send_emails(title, message, recipients):
    """Осуществляет массовую отправку писем каждому адресату в очереди."""
    for recipient in recipients:
        send_email.delay(title, message, recipient)

# Удаление просроченных токенов
@shared_task()
def clean_expired_tokens():
    expiration_days = getattr(settings, 'CONFIRM_EMAIL_TOKEN_EXPIRATION_DAYS', 1)
    expired_date = timezone.now() - timedelta(days=expiration_days)
    ConfirmEmailToken.objects.filter(created_at__lt=expired_date).delete()

# Тестовая функция для демонстрации задержки
def slow_function(limit=10):
    """Демонстрирует задержку с интервалом."""
    count = 0
    while count < limit:
        time.sleep(5)
        count += 1
