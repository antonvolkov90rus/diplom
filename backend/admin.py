from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Настройка отображения и функциональности управления пользователями в админке.
    """
    model = User  # Указываем, с какой моделью работаем

    fieldsets = (  # Настраиваем поля для редактирования
        (None, {'fields': ('email', 'password', 'type')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')  # Поля для отображения в списке


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """Настройка для модели Shop"""
    list_display = ('name', 'url', 'user', 'state')  # Добавлены поля для отображения в списке


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Настройка для модели Category"""
    list_display = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Настройка для модели Product"""
    list_display = ('name', 'category')


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """Настройка для модели ProductInfo"""
    list_display = ('product', 'shop', 'price', 'quantity')


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """Настройка для модели Parameter"""
    list_display = ('name',)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """Настройка для модели ProductParameter"""
    list_display = ('product_info', 'parameter', 'value')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Настройка для модели Order"""
    list_display = ('user', 'dt', 'state', 'contact')  # Добавлены поля для отображения в списке


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Настройка для модели OrderItem"""
    list_display = ('order', 'product_info', 'quantity')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Настройка для модели Contact"""
    list_display = ('user', 'city', 'phone')  # Добавлены поля для отображения в списке


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    """Настройка для модели ConfirmEmailToken"""
    list_display = ('user', 'key', 'created_at',)
