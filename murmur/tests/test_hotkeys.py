from murmur.hotkeys import parse_combo, HoldDetector


def test_parse_combo_basic():
    mods, trigger = parse_combo("alt+space")
    assert mods == frozenset({"alt"})
    assert trigger == "space"


def test_parse_combo_aliases_and_order():
    mods, trigger = parse_combo("Control + Shift + A")
    assert mods == frozenset({"ctrl", "shift"})
    assert trigger == "a"
    assert parse_combo("cmd+v")[0] == frozenset({"win"})


def test_hold_fires_start_then_stop():
    events = []
    d = HoldDetector("alt+space", lambda: events.append("start"), lambda: events.append("stop"))
    d.feed("alt", True)
    assert events == []                 # modifier alone -> nothing
    d.feed("space", True)
    assert events == ["start"]
    assert d.active is True
    d.feed("space", False)
    assert events == ["start", "stop"]
    assert d.active is False


def test_hold_order_independent():
    events = []
    d = HoldDetector("ctrl+shift+a", lambda: events.append("s"), lambda: events.append("e"))
    d.feed("a", True)                   # trigger first
    d.feed("shift", True)
    assert events == []                 # not all mods yet
    d.feed("ctrl", True)
    assert events == ["s"]              # now engaged
    d.feed("ctrl", False)              # releasing a modifier stops it
    assert events == ["s", "e"]


def test_no_double_start():
    events = []
    d = HoldDetector("alt+space", lambda: events.append("s"), lambda: events.append("e"))
    d.feed("alt", True)
    d.feed("space", True)
    d.feed("space", True)              # key repeat
    assert events == ["s"]
