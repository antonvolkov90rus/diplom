from django.test import TestCase, RequestFactory
from django.core.handlers.wsgi import WSGIRequest
from django.urls import reverse
from django.core.handlers.exception import convert_exception_to_response
from django.core.signals import got_request_exception
from django.dispatch import receiver
import rollbar
from unittest.mock import patch


@receiver(got_request_exception)
def handle_uncaught_exception(sender, request=None, *args, **kwargs):
    """
    Пример обработчика исключения, регистрирующий ошибку в Rollbar
    """
    rollbar.report_exc_info()


class TestExceptionHandling(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch.object(rollbar, 'report_exc_info')
    def test_handle_uncaught_exception(self, mock_report_exc_info):
        # Создание фейкового запроса
        request = self.factory.get('/')

        # Фиктивная view-функция, бросающая исключение
        def some_view(request):
            raise Exception("Исключение для тестирования")

        try:
            # Передаем наш запрос фиктивной view-функции
            convert_exception_to_response(some_view)(request)
        except Exception as e:
            # Проверяем, что Rollbar получил уведомление об исключении
            self.assertTrue(mock_report_exc_info.called)

            # Дополнительно проверяем тип исключения и сообщение
            args, kwargs = mock_report_exc_info.call_args
            self.assertIsInstance(args[0], tuple)
            exception_class, exception_instance, tb = args[0]
            self.assertEqual(exception_class, Exception)
            self.assertIn("Исключение для тестирования", str(exception_instance))
        finally:
            # Завершаем тест
            pass