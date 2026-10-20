def test_ninja_canary(collected):
    ninja = [e for e in collected["data"]["endpoints"] if e["kind"] == "ninja"]
    by_version = {}
    for endpoint in ninja:
        by_version[endpoint["api"]["version"]] = by_version.get(endpoint["api"]["version"], 0) + 1
    ok = by_version == {"1.0.0": 12, "2.0.0": 2} and collected["warnings"] == []
    assert ok, (
        "Ninja internals changed: update collectors/ninja_introspect.py "
        f"(operations by API version: {by_version}, warnings: {collected['warnings']})"
    )
