from murmur.modes import (
    Mode, ModeStore, default_modes, build_rewrite_messages,
)


def test_defaults_have_voice_and_unique_ids():
    modes = default_modes()
    ids = [m.id for m in modes]
    assert "voice" in ids
    assert len(ids) == len(set(ids))


def test_voice_is_verbatim():
    voice = next(m for m in default_modes() if m.id == "voice")
    assert voice.rewrites is False
    assert build_rewrite_messages(voice, "hello world") == []


def test_rewrite_messages_structure():
    mail = next(m for m in default_modes() if m.id == "mail")
    assert mail.rewrites is True
    msgs = build_rewrite_messages(mail, "hey can we meet tuesday")
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert "hey can we meet tuesday" in msgs[1]["content"]
    assert "Formal" in msgs[0]["content"]            # tone propagated


def test_context_only_included_when_allowed():
    m = Mode(id="x", name="X", llm_provider="openai", prompt="do it",
             use_selection=True, use_clipboard=False)
    msgs = build_rewrite_messages(m, "the body",
                                  {"selection": "QUOTED", "clipboard": "CLIP", "app": "Gmail"})
    user = msgs[1]["content"]
    assert "QUOTED" in user            # selection allowed
    assert "CLIP" not in user          # clipboard not allowed
    assert "Gmail" not in user         # active app not allowed (use_active_app False)


def test_store_seeds_and_roundtrips(tmp_path):
    p = tmp_path / "modes.json"
    store = ModeStore(path=p)
    assert len(store.list()) == len(default_modes())

    store.upsert(Mode(id="jira", name="Jira", prompt="format as ticket",
                      llm_provider="openai"))
    reloaded = ModeStore(path=p)
    assert reloaded.get("jira") is not None
    assert reloaded.get("jira").name == "Jira"


def test_store_delete(tmp_path):
    store = ModeStore(path=tmp_path / "m.json")
    store.delete("note")
    assert store.get("note") is None


def test_match_auto():
    store = ModeStore(path=None) if False else ModeStore.__new__(ModeStore)
    store._path = None
    store._modes = default_modes()
    assert store.match_auto({"app": "Slack", "title": "", "url": ""}).id == "message"
    assert store.match_auto({"app": "Google Chrome", "title": "Gmail - Inbox"}).id == "mail"
    assert store.match_auto({"app": "Notepad"}) is None
