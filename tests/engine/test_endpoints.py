from pathlib import Path

import pytest
from conftest import SANDBOX, run_engine


def strip(path):
    return path.rstrip("/") or "/"


@pytest.fixture(scope="module")
def endpoints(data):
    return data["endpoints"]


def find(endpoints, method, path):
    return [
        e
        for e in endpoints
        if strip(e["path"]) == path and (method in e["methods"] if method else True)
    ]


def test_ninja_operation_counts(endpoints):
    ninja = [e for e in endpoints if e["kind"] == "ninja"]
    assert len([e for e in ninja if e["api"]["version"] == "1.0.0"]) == 12
    assert len([e for e in ninja if e["api"]["version"] == "2.0.0"]) == 2
    assert {e["api"]["namespace"] for e in ninja} == {"api-v1", "api-v2"}
    assert {e["api"]["title"] for e in ninja if e["api"]["version"] == "1.0.0"} == {"Shop API"}


def test_get_product(endpoints):
    (endpoint,) = find(endpoints, "GET", "/api/v1/products/{product_id}")
    assert endpoint["kind"] == "ninja"
    assert endpoint["view"] == "shop.api.products.get_product"
    assert endpoint["id"] == "ninja:api-v1:GET:/api/v1/products/{product_id}"
    assert endpoint["source"]["file"].endswith("shop/api/products.py")
    assert endpoint["summary"] == "Fetch one product."
    assert endpoint["tags"] == ["products"]
    assert endpoint["signature"].startswith("(request, product_id: int")


@pytest.mark.parametrize("path", ["/api/v1/products", "/api/v1/orders"])
def test_get_and_post_are_separate_endpoints(endpoints, path):
    matches = find(endpoints, None, path)
    assert sorted(e["methods"][0] for e in matches) == ["GET", "POST"]


def test_cancel_order_is_async(endpoints):
    (endpoint,) = [e for e in endpoints if e["view"] == "shop.api.orders.cancel_order"]
    assert endpoint["is_async"] is True
    assert endpoint["methods"] == ["POST"]


def test_class_based_view_points_at_class(data, endpoints):
    url_name = {u["name"]: u for u in data["url_names"]}["blog:post-detail"]
    assert "<slug:slug>" in url_name["route"]
    assert url_name["args"] == ["slug"]
    (endpoint,) = [e for e in endpoints if e["url_name"] == "blog:post-detail"]
    assert endpoint["view"] == "blog.views.PostDetailView"
    assert endpoint["methods"] == ["GET"]
    assert endpoint["path"] == "/blog/{slug}/"
    source = endpoint["source"]
    assert source["file"].endswith("blog/views.py")
    line = Path(source["file"]).read_text().splitlines()[source["line"] - 1]
    assert line.startswith("class PostDetailView")


def test_decorated_view_points_at_views_not_decorator(endpoints):
    (endpoint,) = [e for e in endpoints if e["url_name"] == "blog:archive"]
    assert endpoint["source"]["file"].endswith("blog/views.py")
    assert endpoint["view"] == "blog.views.archive"


def test_regex_route(data, endpoints):
    url_name = {u["name"]: u for u in data["url_names"]}["legacy-detail"]
    assert url_name["args"] == ["pk"]
    assert url_name["namespace"] is None
    assert url_name["route"].startswith("/legacy/")
    assert find(endpoints, None, "/legacy/{pk}")


def test_admin_endpoints_are_django(endpoints):
    admin = [e for e in endpoints if e["path"].startswith("/admin/")]
    assert admin and all(e["kind"] == "django" for e in admin)


def test_sorted_and_ids_use_kinds(endpoints):
    keys = [(e["kind"], e["path"]) for e in endpoints]
    assert keys == sorted(keys)


def test_url_names_include_namespaced_and_ninja(data):
    names = {u["name"] for u in data["url_names"]}
    assert {"home", "shop:cart", "blog:post-list", "api-v1:get_product"} <= names


def test_reverse_ok():
    code, _, env = run_engine(
        "reverse", "--root", str(SANDBOX), "--name", "blog:post-detail", "--kwarg", "slug=hello"
    )
    assert code == 0 and env["ok"] is True
    assert env["data"]["url"] == "/blog/hello/"


def test_reverse_positional_arg():
    code, _, env = run_engine(
        "reverse", "--root", str(SANDBOX), "--name", "blog:archive", "--arg", "2020"
    )
    assert code == 0 and env["data"]["url"] == "/blog/archive/2020/"


def test_reverse_unknown_name():
    code, _, env = run_engine("reverse", "--root", str(SANDBOX), "--name", "no-such-name")
    assert code == 2 and env["ok"] is False
    assert env["error"]["type"] == "NoReverseMatch"


def test_resolve_ninja_health():
    code, _, env = run_engine("resolve", "--root", str(SANDBOX), "--path", "/api/v1/health")
    assert code == 0
    assert env["data"]["view"] == "config.api.health"
    assert env["data"]["url_name"] == "api-v1:health"
    assert env["data"]["source"]["file"].endswith("config/api.py")


def test_resolve_django_view():
    code, _, env = run_engine("resolve", "--root", str(SANDBOX), "--path", "/blog/hello/")
    assert code == 0
    assert env["data"]["view"] == "blog.views.PostDetailView"
    assert env["data"]["url_name"] == "blog:post-detail"
    assert env["data"]["kwargs"] == {"slug": "hello"}


def test_resolve_unknown_path():
    code, _, env = run_engine("resolve", "--root", str(SANDBOX), "--path", "/nope/nope/")
    assert code == 2 and env["error"]["type"] == "Resolver404"
