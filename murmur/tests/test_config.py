from murmur.config import Config, DEFAULTS


def test_defaults_loaded(tmp_path):
    c = Config(path=tmp_path / "s.json")
    assert c.get("theme") == "dark"
    assert c.get("engine") == "auto"
    assert c.get("hotkey") == "alt+space"


def test_set_persists_and_reloads(tmp_path):
    p = tmp_path / "s.json"
    c = Config(path=p)
    c.set("theme", "light")
    c.set("openaiKey", "sk-test")
    c2 = Config(path=p)
    assert c2.get("theme") == "light"
    assert c2.get("openaiKey") == "sk-test"


def test_invalid_enum_falls_back(tmp_path):
    c = Config(path=tmp_path / "s.json")
    assert c.set("theme", "neon") == "dark"          # invalid -> default
    assert c.set("engine", "local") == "local"        # valid kept


def test_bool_coercion(tmp_path):
    c = Config(path=tmp_path / "s.json")
    assert c.set("playSounds", "false") is False
    assert c.set("autoPaste", "on") is True
    assert c.set("trimFillers", 0) is False


def test_unknown_key_ignored(tmp_path):
    c = Config(path=tmp_path / "s.json")
    assert c.set("nope", 1) is None


def test_redact_hides_secrets(tmp_path):
    c = Config(path=tmp_path / "s.json")
    c.set("openaiKey", "sk-secret")
    data = c.all(redact=True)
    assert data["openaiKey"] is True            # presence only
    assert "sk-secret" not in str(data)


def test_subscribe_fires(tmp_path):
    c = Config(path=tmp_path / "s.json")
    seen = []
    c.subscribe(lambda k, v: seen.append((k, v)))
    c.set("theme", "light")
    assert ("theme", "light") in seen
