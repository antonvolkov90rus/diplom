from rest_framework import serializers
from backend.models import User, Category, Shop, ProductInfo, Product, ProductParameter, OrderItem, Order, Contact
from backend.models import ConfirmEmailToken

class ContactSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Contact.
    """
    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True},  # Скрываем поле пользователя при выдаче данных
        }

class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели User.
    """
    contacts = ContactSerializer(many=True, read_only=True)  # Вложенные контакты пользователя

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'company', 'position', 'contacts', 'type')
        read_only_fields = ('id',)

class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Category.
    """
    class Meta:
        model = Category
        fields = ('id', 'name',)
        read_only_fields = ('id',)

class ShopSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Shop.
    """
    class Meta:
        model = Shop
        fields = ('id', 'name', 'state',)
        read_only_fields = ('id',)

class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Product.
    """
    category = serializers.StringRelatedField()  # Выводим категорию в виде строки

    class Meta:
        model = Product
        fields = ('name', 'category',)

class ProductParameterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели ProductParameter.
    """
    parameter = serializers.StringRelatedField()  # Имя параметра выводим текстом

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value',)

class ProductInfoSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели ProductInfo.
    """
    product = ProductSerializer(read_only=True)  # Вложенный сериализатор для товара
    product_parameters = ProductParameterSerializer(many=True, read_only=True)  # Параметры товара

    class Meta:
        model = ProductInfo
        fields = ('id', 'model', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'product_parameters',)
        read_only_fields = ('id',)

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели OrderItem.
    """
    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'order',)
        read_only_fields = ('id',)
        extra_kwargs = {
            'order': {'write_only': True},  # Скрываем поле заказа при выдаче данных
        }

class OrderItemCreateSerializer(OrderItemSerializer):
    """
    Сериализатор для создания элемента заказа.
    """
    product_info = ProductInfoSerializer(read_only=True)  # Дополнительная информация о товаре при создании

class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Order.
    """
    ordered_items = OrderItemCreateSerializer(many=True, read_only=True)  # Элементы заказа
    total_sum = serializers.SerializerMethodField()  # Сумма заказа теперь рассчитывается динамически
    contact = ContactSerializer(read_only=True)  # Контактные данные пользователя

    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'state', 'dt', 'total_sum', 'contact',)
        read_only_fields = ('id',)

    def get_total_sum(self, obj):
        # Новый метод для динамического расчета суммы заказа
        return obj.calculate_total_sum()

class ConfirmEmailTokenSerializer(serializers.Serializer):
    """
    Сериализатор для подтверждения email-пользователя.
    """
    email = serializers.EmailField(required=True)
    key = serializers.CharField(required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        key = attrs.get('key')
        try:
            token = ConfirmEmailToken.objects.get(user__email=email, key=key)
            token.user.is_active = True  # Активируем пользователя
            token.user.save()
            token.delete()  # Удаляем использованный токен
        except ConfirmEmailToken.DoesNotExist:
            raise serializers.ValidationError("Токен или email неверны.")
        return attrs
