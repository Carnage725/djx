from ninja.security import HttpBearer

DEV_TOKEN = "djx-dev-token"


class DevTokenAuth(HttpBearer):
    def authenticate(self, request, token):
        if token == DEV_TOKEN:
            return token
        return None
