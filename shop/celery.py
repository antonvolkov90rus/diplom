import os
from celery import Celery

# Установка DJANGO_SETTINGS_MODULE для использования настроек Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shop.settings")

# Инициализация объекта Celery
app = Celery("shop")

# Загрузка настроек Celery из settings.py вашего Django-проекта
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматическое обнаружение и подключение задач из ваших приложений
app.autodiscover_tasks()