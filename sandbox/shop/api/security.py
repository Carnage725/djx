from ninja.security import HttpBearer

DEV_TOKEN = "djx-dev-token"
PAYMENT_API_KEY = "sk_test_FAKE_123"


class DevTokenAuth(HttpBearer):
    def authenticate(self, request, token):
        if token in (DEV_TOKEN, PAYMENT_API_KEY):
            return token
        return None
