import pytest
import relate

from inforce.store import (
    StoreLocked,
    UnboundedQuery,
    check_bounded,
    open_store,
    query_text,
    split_statements,
)


@pytest.mark.parametrize("q", [
    "MATCH (n) RETURN n",
    "MATCH (n) WITH n RETURN count(n) AS c",
    "MATCH (n) // LIMIT in a comment does not count\nRETURN n",
    "MATCH (n {name: 'LIMIT'}) RETURN n",
])
def test_guard_rejects_unbounded_reads(q):
    with pytest.raises(UnboundedQuery):
        check_bounded(q)


@pytest.mark.parametrize("q", [
    "MATCH (n) RETURN n LIMIT 5",
    "MATCH (n) RETURN count(n) AS c LIMIT 1",
    "RETURN date($on) AS d",
    "UNWIND $rows AS r MERGE (s:Source {url: r.url}) SET s.id = r.id",
    "MATCH (a {id: 1}) MERGE (a)-[:X]->(b:B)",
    "CREATE CONSTRAINT c IF NOT EXISTS FOR (p:P) REQUIRE p.id IS UNIQUE",
])
def test_guard_allows_bounded_reads_and_writes(q):
    check_bounded(q)


def test_split_statements_drops_comments():
    assert split_statements("// a; b\nRETURN 1;\n\n// c\nRETURN 2;") == ["RETURN 1", "RETURN 2"]


def test_query_text_loads_packaged_file():
    assert "LIMIT" in query_text("status_on")


def test_open_creates_and_closes(tmp_path):
    p = tmp_path / "s.rl"
    with open_store(p) as s:
        s.execute("CREATE (:T {x: 1})")
    with open_store(p, read_only=True) as s:
        assert s.execute("MATCH (t:T) RETURN t.x AS x LIMIT 1") == [{"x": 1}]


def test_locked_store_retries_then_raises(tmp_path):
    p = tmp_path / "s.rl"
    holder = relate.connect(database=str(p))
    msgs = []
    try:
        with pytest.raises(StoreLocked) as ei:
            with open_store(p, read_only=True, retries=2, backoff=0.01, log=msgs.append):
                pass
        assert ei.value.exit_code == 5
        assert len(msgs) == 2
    finally:
        holder.close()


def test_lock_released_between_retries(tmp_path):
    p = tmp_path / "s.rl"
    holder = relate.connect(database=str(p))
    # Connections are thread-affine, so release the lock from the retry hook on this thread.
    released = []

    def log(msg):
        if not released:
            holder.close()
            released.append(msg)
    with open_store(p, retries=3, backoff=0.01, log=log) as s:
        assert s.execute("RETURN 1 AS one") == [{"one": 1}]
    assert len(released) == 1


def test_rollback_only_leaves_store_unchanged(tmp_path):
    p = tmp_path / "s.rl"
    with open_store(p) as s:
        s.execute("CREATE (:T)")
        with s.rollback_only():
            s.execute("CREATE (:T)")
            assert s.execute("MATCH (t:T) RETURN count(t) AS c LIMIT 1")[0]["c"] == 2
        assert s.execute("MATCH (t:T) RETURN count(t) AS c LIMIT 1")[0]["c"] == 1


def test_transaction_rolls_back_on_error(tmp_path):
    p = tmp_path / "s.rl"
    with open_store(p) as s:
        with pytest.raises(RuntimeError), s.transaction():
            s.execute("CREATE (:T)")
            raise RuntimeError("boom")
        assert s.execute("MATCH (t:T) RETURN count(t) AS c LIMIT 1")[0]["c"] == 0
