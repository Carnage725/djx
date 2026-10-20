# sandbox

Dummy Django + Django Ninja project that djx inspects. Run from the repo root with `uv run python sandbox/manage.py ...`. Deliberately full of edge cases.

## Edge cases

- **Two Ninja APIs** (`api-v1` Shop API 1.0.0 with 12 operations, `api-v2` 2.0.0 with 2): tests grouping by API and per-API counts.
- **Routers in separate files** (`shop/api/products.py`, `orders.py`, `auth.py`, `v2.py`): source locations must differ per endpoint.
- **Operation defined directly on the API** (`/health` in `config/api.py`): no router involved.
- **Same path, several methods** (`/products`, `/orders`): must expand to one endpoint per method.
- **Async operation** (`cancel_order`): tests `is_async`.
- **Auth on some operations only** (`HttpBearer`, token `djx-dev-token`).
- **Router mounted at `""`** (v2): tests path concatenation with an empty prefix.
- **Namespaced includes** (`shop`, `blog` via `app_name`): tests full url names like `blog:post-detail`.
- **Class-based views** (`PostListView`, `PostDetailView`): source must point at the class.
- **Decorated view** (`archive` wrapped by `@timed`, which lives in `blog/decorators.py`): source must point at `blog/views.py`, not the decorator.
- **Regex route** (`legacy-detail`, `re_path`): tests regex routes and group names.
- **Admin URLs**: many plain Django patterns from a third-party-style include.
- **Import-time `print`** in `blog/views.py`: engine stdout must stay clean JSON.
- **Abstract model** (`core.TimeStampedModel`): must not appear in models.
- **Proxy model** (`shop.ActiveProduct`) with a filtering default manager.
- **Self FK** (`Category.parent`), **O2O** (`Customer.user`, `Author.user`), **M2M** (`Post.tags`), **related_name** (`products`, `items`).
- **Choices field** (`Order.status`).
- **Management commands** with help strings: `seed_shop`, `export_orders`, `seed_blog`.
- **Broken settings** (`config/settings_broken.py`): imports a missing module, tests the error screen. Use `DJANGO_SETTINGS_MODULE=config.settings_broken`.
