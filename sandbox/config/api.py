from ninja import NinjaAPI

from shop.api.auth import router as auth_router
from shop.api.orders import router as orders_router
from shop.api.products import router as products_router
from shop.api.v2 import router as v2_router

api_v1 = NinjaAPI(title="Shop API", version="1.0.0", urls_namespace="api-v1")
api_v1.add_router("/products", products_router)
api_v1.add_router("/orders", orders_router)
api_v1.add_router("/auth", auth_router)


@api_v1.get("/health")
def health(request):
    return {"status": "ok"}


api_v2 = NinjaAPI(version="2.0.0", urls_namespace="api-v2")
api_v2.add_router("", v2_router)
