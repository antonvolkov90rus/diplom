from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django.core.mail import EmailMessage
from backend.models import User, ConfirmEmailToken
from backend.utils import generate_token
from drf_spectacular.utils import extend_schema
from requests import get
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets
from yaml import load as load_yaml, Loader

from backend.models import Shop, Category, Product, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken, ProductInfo
from backend.serializers import UserSerializer, CategorySerializer, ShopSerializer, \
    OrderItemSerializer, OrderSerializer, ContactSerializer, ProductInfoSerializer

from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created
from backend.tasks import send_email


# Сигнал для отправки токена сброса пароля
@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    Отправляем письмо с токеном для сброса пароля
    """
    send_email.delay(
        subject=f"Сброс пароля для {reset_password_token.user}",
        body=reset_password_token.key,
        recipient_list=[reset_password_token.user.email]
    )


class RegisterAccount(APIView):
    """
    Для регистрации покупателей
    """

    @extend_schema(request=UserSerializer, responses=UserSerializer)
    def post(self, request, *args, **kwargs):
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            errors = {}

            # Проверяем пароль на сложность
            try:
                validate_password(request.data['password'])
            except ValidationError as err:
                return JsonResponse({'Status': False, 'Errors': {'password': list(err.messages)}})

            # Проверяем данные на уникальность
            user_serializer = UserSerializer(data=request.data)
            if user_serializer.is_valid():
                user = user_serializer.save()
                user.set_password(request.data['password'])
                user.save()
                token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
                send_email.delay("Регистрация успешна", f"Токен подтверждения: {token.key}", user.email)
                return JsonResponse({'Status': True, 'confirm_token': token.key})
            else:
                return JsonResponse({'Status': False, 'Errors': user_serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    @extend_schema(request=None, responses=None)
    def post(self, request, *args, **kwargs):
        if {'email', 'token'}.issubset(request.data):
            token_obj = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                         key=request.data['token']).first()
            if token_obj:
                token_obj.user.is_active = True
                token_obj.user.save()
                token_obj.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильный токен или email'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class AccountDetails(APIView):
    """
    Класс для работы с данными пользователя
    """

    @extend_schema(request=UserSerializer, responses=UserSerializer)
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(request=UserSerializer, responses=UserSerializer)
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)

        if 'password' in request.data:
            try:
                validate_password(request.data['password'])
            except ValidationError as err:
                return JsonResponse({'Status': False, 'Errors': {'password': list(err.messages)}})
            else:
                request.user.set_password(request.data['password'])

        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """

    @extend_schema(request=None, responses=None)
    def post(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(username=request.data['email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    return JsonResponse({'Status': True, 'Token': token.key})
                else:
                    return JsonResponse({'Status': False, 'Errors': 'Аккаунт неактивен'})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неудачная авторизация'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя
    """

    @extend_schema(request=OrderSerializer, responses=OrderSerializer)
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)
        basket = Order.objects.filter(user_id=request.user.id, state='basket').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))
        ).distinct()
        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    @extend_schema(request=OrderItemSerializer, responses=OrderItemSerializer)
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)
        items_string = request.data.get('items')
        if items_string:
            try:
                items_dict = eval(items_string)
            except SyntaxError:
                return JsonResponse({'Status': False, 'Errors': 'Некорректный формат данных'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({'order': basket.id})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                            objects_created += 1
                        except IntegrityError as err:
                            return JsonResponse({'Status': False, 'Errors': str(err)})
                    else:
                        return JsonResponse({'Status': False, 'Errors': serializer.errors})

                return JsonResponse({'Status': True, 'Создано объектов': objects_created})
        return JsonResponse({'Status': False, 'Errors': 'Нет необходимых аргументов'})

    @extend_schema(request=None, responses=None)
    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)
        items_string = request.data.get('items')
        if items_string:
            items_list = items_string.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query |= Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Нет необходимых аргументов'})

    @extend_schema(request=None, responses=None)
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)
        items_string = request.data.get('items')
        if items_string:
            try:
                items_dict = eval(items_string)
            except SyntaxError:
                return JsonResponse({'Status': False, 'Errors': 'Некорректный формат данных'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                for order_item in items_dict:
                    if isinstance(order_item['id'], int) and isinstance(order_item['quantity'], int):
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity']
                        )

                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
        return JsonResponse({'Status': False, 'Errors': 'Нет необходимых аргументов'})


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """

    @extend_schema(request=None, responses=None)
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Доступ ограничен'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as err:
                return JsonResponse({'Status': False, 'Error': str(err)}, status=400)
            else:
                response = get(url)
                data = load_yaml(response.content, Loader=Loader)

                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
                for category_data in data['categories']:
                    category, _ = Category.objects.get_or_create(id=category_data['id'], name=category_data['name'])
                    category.shops.add(shop.id)
                    category.save()

                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for good in data['goods']:
                    product, _ = Product.objects.get_or_create(name=good['name'], category_id=good['category'])

                    product_info = ProductInfo.objects.create(
                        product_id=product.id,
                        external_id=good['id'],
                        model=good['model'],
                        price=good['price'],
                        price_rrc=good['price_rrc'],
                        quantity=good['quantity'],
                        shop_id=shop.id
                    )

                    for param_name, param_value in good['parameters'].items():
                        parameter, _ = Parameter.objects.get_or_create(name=param_name)
                        ProductParameter.objects.create(
                            product_info_id=product_info.id,
                            parameter_id=parameter.id,
                            value=param_value
                        )

                return JsonResponse({'Status': True}, status=200)

        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'}, status=400)


class PartnerState(APIView):
    """
    Класс для работы со статусом поставщика
    """

    @extend_schema(request=None, responses=ShopSerializer)
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Доступ ограничен'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    @extend_schema(request=None, responses=None)
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Доступ ограничен'}, status=403)
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=(state.lower() == 'true'))
                return JsonResponse({'Status': True}, status=200)
            except ValueError as err:
                return JsonResponse({'Status': False, 'Error': str(err)}, status=400)

        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'}, status=400)


class PartnerOrders(APIView):
    """
    Класс для получения заказов поставщиками
    """

    @extend_schema(request=None, responses=OrderSerializer)
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Доступ ограничен'}, status=403)

        orders = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id
        ).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter'
        ).select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))
        ).distinct()

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class ContactView(APIView):
    """
    Класс для работы с контактами покупателей
    """

    @extend_schema(request=None, responses=ContactSerializer)
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)
        contacts = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    @extend_schema(request=ContactSerializer, responses=None)
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)

        if {'city', 'street', 'phone'}.issubset(request.data):
            data = request.data.copy()
            data.update({'user': request.user.id})
            serializer = ContactSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True}, status=201)
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors}, status=400)

        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'}, status=400)

    @extend_schema(request=None, responses=None)
    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)

        items_string = request.data.get('items')
        if items_string:
            items_list = items_string.split(',')
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query |= Q(user_id=request.user.id, id=contact_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count}, status=200)
        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'}, status=400)

    @extend_schema(request=ContactSerializer, responses=ContactSerializer)
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется авторизация'}, status=403)

        if 'id' in request.data:
            if request.data['id'].isdigit():
                contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
                if contact:
                    serializer = ContactSerializer(contact, data=request.data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return JsonResponse({'Status': True}, status=200)
                    else:
                        return JsonResponse({'Status': False, 'Errors': serializer.errors}, status=400)
                else:
                    return JsonResponse({'Status': False, 'Error': 'Контакт не найден'}, status=404)
        return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'}, status=400)


class OrderView(APIView):
    """
    Класс для получения и размешения заказов пользователями
    """

    # получить мои заказы
    @extend_schema(request=None, responses=OrderSerializer)
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        order = Order.objects.filter(
            user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    # разместить заказ из корзины
    @extend_schema(request=None, responses=None)
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'id', 'contact'}.issubset(request.data):
            if request.data['id'].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data['id']).update(
                        contact_id=request.data['contact'],
                        state='new')
                except IntegrityError as error:
                    print(error)
                    return JsonResponse({'Status': False, 'Errors': 'Неправильно указаны аргументы'})
                else:
                    if is_updated:
                        # new_order_task(sender=self.__class__, user_id=request.user.id)
                        user = request.user
                        send_email.delay("Обновление статуса заказа",
                                         "Заказ сформирован",
                                         user.email)
                        return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ProductInfoView(viewsets.ModelViewSet):
    """
    Класс для поиска товаров
    """
    queryset = ProductInfo.objects.get_queryset().order_by('id')
    serializer_class = ProductInfoSerializer
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):

        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        # фильтруем и отбрасываем дуликаты
        queryset = ProductInfo.objects.filter(
            query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)
