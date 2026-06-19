import time

from murmur.history import History, _fmt_ago, _fmt_dur


def test_fmt_dur():
    assert _fmt_dur(0) == "0:00"
    assert _fmt_dur(9) == "0:09"
    assert _fmt_dur(75) == "1:15"
    assert _fmt_dur(758) == "12:38"


def test_fmt_ago():
    now = 1_000_000.0
    assert _fmt_ago(now - 5, now) == "just now"
    assert _fmt_ago(now - 120, now) == "2 min ago"
    assert _fmt_ago(now - 3600, now) == "1 hr ago"
    assert _fmt_ago(now - 7200, now) == "2 hrs ago"
    assert _fmt_ago(now - 86400, now) == "Yesterday"
    assert _fmt_ago(now - 3 * 86400, now) == "3 days ago"


def test_add_list_search(tmp_path):
    h = History(path=tmp_path / "h.db")
    h.add(mode_id="mail", mode_name="Mail", glyph="✉️",
          raw="hey", text="Hello there, scheduling a meeting.", duration=12.0)
    h.add(mode_id="voice", mode_name="Voice", glyph="✶",
          raw="numbers", text="The quarterly numbers look strong.", duration=8.0)

    allrows = h.list()
    assert len(allrows) == 2
    assert allrows[0]["mode"] == "Voice"          # newest first
    assert allrows[0]["words"] == 5

    found = h.list(query="meeting")
    assert len(found) == 1
    assert found[0]["mode"] == "Mail"


def test_stats(tmp_path):
    h = History(path=tmp_path / "h.db")
    h.add(mode_id="v", mode_name="Voice", glyph="✶",
          raw="x", text="one two three four five six seven eight", duration=4.0)
    s = h.stats()
    assert s["sessions"] == 1
    assert s["words"] == 8
    assert s["minutesSaved"] >= 0


def test_delete(tmp_path):
    h = History(path=tmp_path / "h.db")
    rid = h.add(mode_id="v", mode_name="V", glyph="✶", raw="a", text="abc", duration=1.0)
    h.delete(rid)
    assert h.list() == []
