from django.contrib.auth import authenticate
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from backend.serializers import UserSerializer, ConfirmEmailTokenSerializer
from backend.models import ConfirmEmailToken
from backend.tasks import send_email

class RegisterAccount(APIView):
    """
    Регистрация нового пользователя.
    Возвращает токен подтверждения, который необходимо передать для активации аккаунта.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data['password'])
            user.save()
            token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
            send_email.delay("Confirmation of registration", f"Your confirmation token {token.key}", user.email)
            return JsonResponse({'Status': True, 'confirm_token': token.key})
        else:
            return JsonResponse({'Status': False, 'Errors': serializer.errors})

class ConfirmAccount(APIView):
    """
    Подтверждение email-аккаунта пользователя по токену.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ConfirmEmailTokenSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['key']
            email = serializer.validated_data['email']
            user_token = ConfirmEmailToken.objects.filter(key=token, user__email=email).first()
            if user_token:
                user_token.user.is_active = True
                user_token.user.save()
                user_token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан токен или email'})
        else:
            return JsonResponse({'Status': False, 'Errors': serializer.errors})

class LoginAccount(APIView):
    """
    Вход пользователя с получением токена аутентификации.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(username=request.data['email'], password=request.data['password'])
            if user is not None:
                token, _ = Token.objects.get_or_create(user=user)
                return JsonResponse({'Status': True, 'Token': token.key})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизоваться'})
        else:
            return JsonResponse({'Status': False, 'Errors': 'Необходимо указать email и пароль'})
