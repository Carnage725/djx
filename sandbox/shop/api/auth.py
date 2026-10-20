from django.contrib.auth import authenticate
from ninja import Router
from ninja.errors import HttpError

from shop.api.schemas import LoginIn, TokenOut, UserOut
from shop.api.security import DEV_TOKEN, DevTokenAuth

router = Router(tags=["auth"])


@router.post("/login", response=TokenOut)
def login(request, payload: LoginIn):
    """Exchange credentials for the dev token."""
    user = authenticate(request, username=payload.username, password=payload.password)
    if user is None:
        raise HttpError(401, "Invalid credentials")
    return {"token": DEV_TOKEN}


@router.get("/me", response=UserOut, auth=DevTokenAuth())
def me(request):
    """Return the first user (the dev token has no user attached)."""
    from django.contrib.auth import get_user_model

    return get_user_model().objects.order_by("id").first()
