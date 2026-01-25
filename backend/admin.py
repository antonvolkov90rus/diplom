from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, Contact, ConfirmEmailToken


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser')


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'user', 'state')
    list_filter = ('state', 'categories')
    search_fields = ('name', 'url', 'user__email')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Настройка для модели Category"""
    list_display = ('name',)


@admin.register(Product)  # Регистрация модели Product
class ProductAdmin(admin.ModelAdmin):
    search_fields = ('name',)  # Необходимо для поддержки autocomplete_fields


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """
    Настройка представления и функционала для модели ProductInfo в админке.
    """
    list_display = ('product', 'shop', 'external_id', 'model', 'price', 'quantity', 'price_rrc')
    search_fields = ('product__name', 'shop__name', 'external_id', 'model')
    list_filter = ('shop', 'product__category')
    ordering = ('product',)
    readonly_fields = ('price_rrc',)
    autocomplete_fields = ('product', 'shop')
    save_on_top = True
    date_hierarchy = 'updated_at'  # Предполагая, что поле создано
    list_per_page = 20
    list_select_related = ('product', 'shop')
    show_full_result_count = False


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
    list_display = ('user', 'dt', 'state', 'contact')
    list_filter = ('state', 'dt')
    ordering = ('-dt',)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Настройка для модели OrderItem"""
    list_display = ('order', 'product_info', 'quantity')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Настройка для модели Contact"""
    list_display = ('user', 'city', 'phone')


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    """Настройка для модели ConfirmEmailToken"""
    list_display = ('user', 'key', 'created_at',)