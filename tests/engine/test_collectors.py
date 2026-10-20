def field(model, name):
    return next(f for f in model["fields"] if f["name"] == name)


def test_no_warnings(collected):
    assert collected["warnings"] == []


def test_apps(data):
    apps = {a["label"]: a for a in data["apps"]}
    for label in ("core", "shop", "blog"):
        assert apps[label]["origin"] == "local"
    assert apps["auth"]["origin"] == "django"
    assert apps["ninja"]["origin"] == "third_party"
    assert apps["shop"]["model_count"] == 6
    assert apps["shop"]["command_count"] == 2


def test_product_fk_category(models_by_label):
    rel = field(models_by_label["shop.Product"], "category")["relation"]
    assert rel["kind"] == "fk"
    assert rel["to"] == "shop.Category"
    assert rel["related_name"] == "products"
    assert rel["on_delete"] == "CASCADE"


def test_category_self_fk(models_by_label):
    rel = field(models_by_label["shop.Category"], "parent")["relation"]
    assert rel["kind"] == "fk" and rel["to"] == "shop.Category"


def test_post_m2m_tags(models_by_label):
    rel = field(models_by_label["blog.Post"], "tags")["relation"]
    assert rel["kind"] == "m2m" and rel["to"] == "blog.Tag"
    assert rel["on_delete"] is None and rel["through"] is None


def test_customer_o2o_user(models_by_label):
    rel = field(models_by_label["shop.Customer"], "user")["relation"]
    assert rel["kind"] == "o2o" and rel["to"] == "auth.User"


def test_proxy_model(models_by_label):
    active = models_by_label["shop.ActiveProduct"]
    assert active["proxy"] is True
    assert active["proxy_for"] == "shop.Product"
    assert models_by_label["shop.Product"]["proxy"] is False


def test_abstract_model_absent(models_by_label):
    assert "core.TimeStampedModel" not in models_by_label


def test_product_source(models_by_label):
    source = models_by_label["shop.Product"]["source"]
    assert source["file"].endswith("shop/models.py")
    assert isinstance(source["line"], int)


def test_product_reverse_relations(models_by_label):
    reverse = models_by_label["shop.Product"]["reverse_relations"]
    assert {"name": "orderitem_set", "kind": "fk", "from": "shop.OrderItem", "field": "product"} in reverse
    category = models_by_label["shop.Category"]["reverse_relations"]
    assert {"name": "products", "kind": "fk", "from": "shop.Product", "field": "category"} in category


def test_field_basics(models_by_label):
    product = models_by_label["shop.Product"]
    assert product["pk"] == "id" and product["db_table"] == "shop_product"
    assert field(product, "category")["column"] == "category_id"
    assert field(product, "sku")["unique"] is True
    assert field(product, "sku")["max_length"] == 32
    assert field(product, "is_active")["default"] == "True"
    assert field(models_by_label["shop.Order"], "status")["has_choices"] is True
    assert field(models_by_label["blog.Post"], "tags")["column"] is None


def test_commands(data):
    commands = {c["name"]: c for c in data["commands"]}
    for name in ("seed_shop", "export_orders", "seed_blog"):
        assert commands[name]["origin"] == "local"
        assert commands[name]["help"]
        assert commands[name]["source"]["file"].endswith(f"management/commands/{name}.py")
    assert commands["seed_shop"]["app"] == "shop"
    assert commands["migrate"]["origin"] == "django"
    # local commands come first
    origins = [c["origin"] for c in data["commands"]]
    assert origins == sorted(origins, key={"local": 0, "third_party": 1, "django": 2}.get)


def test_engine_stdout_is_clean_json(collected):
    # The fixture already json.loads the whole stdout; any stray print would have failed it.
    assert collected["ok"] is True
