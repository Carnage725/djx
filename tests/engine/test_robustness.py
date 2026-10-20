import json
import textwrap

from conftest import SANDBOX, run_engine, run_with_driver


def test_broken_settings(tmp_path):
    code, stdout, env = run_engine(
        "collect", "--root", str(SANDBOX), "--settings", "config.settings_broken"
    )
    assert code == 2
    assert env["ok"] is False
    assert env["error"]["type"]
    assert env["error"]["hint"]
    assert env["error"]["traceback"]
    assert json.loads(stdout) == env  # stdout is exactly one JSON document


def test_other_cwd(tmp_path):
    proc = run_with_driver("", "collect", "--root", str(SANDBOX), cwd=tmp_path)
    assert proc.returncode == 0
    env = json.loads(proc.stdout)
    assert env["ok"] is True
    assert env["project"]["root"] == str(SANDBOX)
    assert {a["label"] for a in env["data"]["apps"]} >= {"core", "shop", "blog"}


def test_failing_collector_becomes_warning():
    driver = textwrap.dedent(
        """
        from djx_engine import collectors

        def boom():
            raise RuntimeError("boom")

        collectors.COLLECTORS[:] = [
            (key, boom if key == "models" else fn) for key, fn in collectors.COLLECTORS
        ]
        """
    )
    proc = run_with_driver(driver, "collect", "--root", str(SANDBOX))
    assert proc.returncode == 0
    env = json.loads(proc.stdout)
    assert env["ok"] is True
    assert env["data"]["models"] == []
    assert env["data"]["apps"] and env["data"]["endpoints"] and env["data"]["commands"]
    assert env["warnings"] == [{"collector": "models", "message": "RuntimeError: boom"}]
    assert "boom" in proc.stderr  # traceback goes to stderr, never stdout


def make_plain_project(tmp_path):
    (tmp_path / "manage.py").write_text(
        "import os\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plain_settings')\n"
    )
    (tmp_path / "plain_settings.py").write_text(
        "SECRET_KEY = 'x'\nINSTALLED_APPS = []\nROOT_URLCONF = 'plain_urls'\nUSE_TZ = True\n"
    )
    (tmp_path / "plain_urls.py").write_text(
        "from django.http import HttpResponse\nfrom django.urls import path\n\n\n"
        "def hello(request):\n    return HttpResponse('hi')\n\n\n"
        "urlpatterns = [path('hello/', hello, name='hello')]\n"
    )


def test_project_without_ninja(tmp_path):
    make_plain_project(tmp_path)
    # Block `import ninja` and hide its package metadata, as if it were not installed.
    driver = textwrap.dedent(
        """
        import importlib.metadata as md

        sys.modules["ninja"] = None
        real_version = md.version

        def version(name):
            if name == "django-ninja":
                raise md.PackageNotFoundError(name)
            return real_version(name)

        md.version = version
        """
    )
    proc = run_with_driver(driver, "collect", "--root", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    env = json.loads(proc.stdout)
    assert env["ok"] is True
    assert env["project"]["ninja_version"] is None
    assert env["warnings"] == []
    (hello,) = [e for e in env["data"]["endpoints"] if e["path"] == "/hello/"]
    assert hello["kind"] == "django"
    assert hello["view"] == "plain_urls.hello"
    assert hello["origin"] == "local"
