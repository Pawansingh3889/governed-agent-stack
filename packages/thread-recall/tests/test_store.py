"""Tests for the governed agent-memory store (SQLite backend)."""
import sys

from thread_recall.store import Memory, _cosine


def test_remember_and_recent_chronological():
    mem = Memory(":memory:")
    mem.remember("t1", "user", "first")
    mem.remember("t1", "assistant", "second")
    mem.remember("t1", "user", "third")
    turns = mem.recent("t1")
    assert [t.content for t in turns] == ["first", "second", "third"]
    assert [t.role for t in turns] == ["user", "assistant", "user"]


def test_recent_respects_k_and_keeps_latest():
    mem = Memory(":memory:")
    for i in range(5):
        mem.remember("t1", "user", f"msg{i}")
    turns = mem.recent("t1", k=2)
    assert [t.content for t in turns] == ["msg3", "msg4"]


def test_threads_are_isolated():
    mem = Memory(":memory:")
    mem.remember("a", "user", "for a")
    mem.remember("b", "user", "for b")
    assert [t.content for t in mem.recent("a")] == ["for a"]
    assert mem.count("a") == 1
    assert mem.count() == 2


def test_semantic_search_returns_nearest():
    mem = Memory(":memory:")
    mem.remember("t1", "user", "revenue question", embedding=[1.0, 0.0, 0.0])
    mem.remember("t1", "assistant", "revenue answer", embedding=[0.9, 0.1, 0.0])
    mem.remember("t1", "user", "weather", embedding=[0.0, 0.0, 1.0])
    hits = mem.search("t1", [1.0, 0.0, 0.0], k=2)
    assert [h.content for h in hits] == ["revenue question", "revenue answer"]
    assert hits[0].score >= hits[1].score
    # the unrelated turn is not in the top-2
    assert "weather" not in [h.content for h in hits]


def test_search_ignores_turns_without_embeddings():
    mem = Memory(":memory:")
    mem.remember("t1", "user", "no embedding")
    mem.remember("t1", "user", "has embedding", embedding=[1.0, 0.0])
    hits = mem.search("t1", [1.0, 0.0], k=5)
    assert [h.content for h in hits] == ["has embedding"]


def test_forget_clears_thread():
    mem = Memory(":memory:")
    mem.remember("t1", "user", "x")
    mem.remember("t1", "user", "y")
    removed = mem.forget("t1")
    assert removed == 2
    assert mem.recent("t1") == []


def test_metadata_round_trips():
    mem = Memory(":memory:")
    mem.remember("t1", "user", "x", metadata={"tool": "get_metric", "rows": 3})
    t = mem.recent("t1")[0]
    assert t.metadata == {"tool": "get_metric", "rows": 3}


def test_mask_true_is_graceful_without_pii_veil(monkeypatch):
    """pii-veil is optional; with it absent, mask=True must not crash and stores as-is.

    Absence is simulated rather than inherited from the environment. This test
    used to pass only because pii-veil happened not to be installed, so it
    quietly became a no-op wherever it was — including any checkout that
    installs the whole stack together, where the real Veil pulls in presidio
    and tries to download a spaCy model at import. Blocking the import makes
    the invariant hold regardless of what else is present.
    """
    monkeypatch.setitem(sys.modules, "pii_veil", None)
    mem = Memory(":memory:", mask=True)
    mem.remember("t1", "user", "email me at a@b.com")
    assert mem.count("t1") == 1


def test_mask_survives_a_veil_that_exits_the_interpreter(monkeypatch):
    """A failed spaCy model download raises SystemExit, not Exception.

    pii-veil's presidio backend fetches a model the first time a Veil is built,
    and spacy.cli calls sys.exit() when that fetch fails — offline, behind a
    proxy, or in CI. SystemExit derives from BaseException, so an `except
    Exception` guard misses it and the process dies on import. mask=True is
    documented as optional, so it must degrade instead.
    """
    import types

    fake = types.ModuleType("pii_veil")

    def _explode(*_a, **_k):
        raise SystemExit(1)

    fake.Veil = _explode
    monkeypatch.setitem(sys.modules, "pii_veil", fake)

    mem = Memory(":memory:", mask=True)
    mem.remember("t1", "user", "email me at a@b.com")
    assert mem.count("t1") == 1


def test_cosine_basics():
    assert _cosine([1, 0], [1, 0]) == 1.0
    assert _cosine([1, 0], [0, 1]) == 0.0
    assert _cosine([], [1]) == 0.0
