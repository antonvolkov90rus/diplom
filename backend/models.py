from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.db.models import F, Sum
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator
from easy_thumbnails.fields import ThumbnailerImageField

# Статусы заказа
ORDER_STATUS_CHOICES = (
    ('draft', 'Черновик'),
    ('processing', 'В обработке'),
    ('completed', 'Завершен'),
    ('cancelled', 'Отменён'),
)

# Типы пользователей
USER_TYPES = (
    ('admin', 'Администратор'),
    ('manager', 'Менеджер'),
    ('customer', 'Клиент'),
)


class UserManager(BaseUserManager):
    """Менеджер для управления пользователями."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Необходимо указать email')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь статус staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь статус superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Пользовательская модель."""

    email = models.EmailField(unique=True)
    avatar = ThumbnailerImageField(upload_to='avatars/', blank=True, null=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='customer')
    company = models.CharField(max_length=100, blank=True, verbose_name=_('Компания'))
    position = models.CharField(max_length=100, blank=True, verbose_name=_('Должность'))

    objects = UserManager()

    def __str__(self):
        return self.email


class Category(models.Model):
    """Категории товаров."""

    name = models.CharField(max_length=40)

    def __str__(self):
        return self.name


class Product(models.Model):
    """Описание товара."""

    name = models.CharField(max_length=80)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    image = ThumbnailerImageField(upload_to='products/', blank=True, null=True)

    def __str__(self):
        return self.name


class Shop(models.Model):
    """Магазины."""

    name = models.CharField(max_length=50)
    url = models.URLField(null=True, blank=True)
    state = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    """Детали товара в магазине."""

    product = models.ForeignKey(Product, related_name='infos', on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, related_name='product_infos', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} ({self.shop.name})"


class Parameter(models.Model):
    """Параметры товаров."""

    name = models.CharField(max_length=40)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    """Связь товаров с параметрами."""

    product_info = models.ForeignKey(ProductInfo, related_name='parameters', on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, related_name='product_parameters', on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.parameter}: {self.value}"


class Contact(models.Model):
    """Контакты пользователя."""

    user = models.ForeignKey(User, related_name='contacts', on_delete=models.CASCADE)
    city = models.CharField(max_length=50)
    street = models.CharField(max_length=100)
    house = models.CharField(max_length=15, blank=True)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user.email}'s contact info"


class Order(models.Model):
    user = models.ForeignKey(User, related_name='orders', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='draft')
    date_created = models.DateTimeField(auto_now_add=True)

    @property
    def contact_details(self):
        try:
            return self.user.contacts.first()
        except AttributeError:
            return None

    @property
    def total_price(self):
        return self.items.aggregate(Sum(F('quantity') * F('product_info__price')))['sum']

    def __str__(self):
        return f"Order #{self.id} by {self.user.email}"


class OrderItem(models.Model):
    """Позиции заказа."""

    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_info = models.ForeignKey(ProductInfo, related_name='order_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity}x {self.product_info.product.name}"


class ConfirmEmailToken(models.Model):
    """Токены подтверждения email."""

    user = models.ForeignKey(User, related_name='tokens', on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token for {self.user.email}"
