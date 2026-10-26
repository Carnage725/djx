from ninja.security import HttpBearer

DEV_TOKEN = "djx-dev-token"
PAYMENT_API_KEY = "gCJhyIA5VANTfqGHSYkLgWTI"


class DevTokenAuth(HttpBearer):
    def authenticate(self, request, token):
        if token in (DEV_TOKEN, PAYMENT_API_KEY):
            return token
        return None
