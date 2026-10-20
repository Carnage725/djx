from django.contrib import admin
from django.urls import include, path, re_path

from blog.views import legacy_detail
from config.api import api_v1, api_v2
from config.views import home

urlpatterns = [
    path("", home, name="home"),
    path("", include("shop.urls")),
    path("", include("blog.urls")),
    re_path(r"^legacy/(?P<pk>[0-9]+)/$", legacy_detail, name="legacy-detail"),
    path("admin/", admin.site.urls),
    path("api/v1/", api_v1.urls),
    path("api/v2/", api_v2.urls),
]
