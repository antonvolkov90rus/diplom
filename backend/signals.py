from django.core.handlers.base import BaseHandler
from django.core.signals import got_request_exception
from django.dispatch import Signal
import rollbar

# Обработчик необрабатываемых исключений
def handle_uncaught_exception(sender, request, exc_type, exc_value, traceback):
    # Отчёт об ошибке с использованием Rollbar
    rollbar.report_exc_info((exc_type, exc_value, traceback))

# Регистрация обработчика сигнала
got_request_exception.connect(handle_uncaught_exception)