"""Agent surfaces: recording answers, two writers on one project graph, the MCP server."""
import asyncio
import json
import shutil
import subprocess
import sys

import pytest

from inforce.scan import record_answer, scan

from .test_check import STALE
from .test_scan import repo  # noqa: F401  (fixture)

HOLDER = """
import sys, time
from inforce.store import open_store
with open_store(sys.argv[1]) as s:
    s.execute("RETURN 1 AS ok")
    print("held", flush=True)
    time.sleep(float(sys.argv[2]))
"""


def test_record_answer_is_tracked_and_survives_scan(repo, law_pack):  # noqa: F811
    path, _ = law_pack
    r = record_answer(repo, "a1", STALE.read_text(), "2026-03-01", path)
    assert r["verdict"] == "STALE" and r["artifact"]["id"] == "agent/a1"
    rep = scan(repo, "2026-03-01", path)
    [agent] = [a for a in rep["artifacts"] if a["id"] == "agent/a1"]
    assert agent["status"] == "STALE" and agent["origin"] == "agent"
    # re-recording a fixed answer replaces it
    r2 = record_answer(repo, "a1", "Under the Nigeria Tax Act the first NGN 800,000 is taxed at 0%.", "2026-03-01", path)
    assert r2["verdict"] == "SUSPECT"  # current law, unverified


def test_second_writer_retries_while_first_holds_the_store(repo, law_pack):  # noqa: F811
    path, _ = law_pack
    scan(repo, "2026-03-01", path)
    store = repo / ".inforce" / "project.rl"
    holder = subprocess.Popen([sys.executable, "-c", HOLDER, str(store), "0.6"], stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == "held"
    logs = []
    r = record_answer(repo, "a2", "Under PITA.", "2026-03-01", path, log=logs.append)
    holder.wait()
    assert logs and all("store locked, retry" in m for m in logs)
    assert r["artifact"]["id"] == "agent/a2"


async def _mcp_round_trip(law):
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
    params = StdioServerParameters(command=shutil.which("inforce"), args=["serve", "--law", str(law)])
    async with Client(params) as c:
        names = sorted(t.name for t in (await c.list_tools()).tools)
        res = await c.call_tool("inforce_check", {"text": "the first ₦300,000 at 7%", "on": "2026-03-01"})
        return names, json.loads(res.content[0].text)


@pytest.mark.skipif(shutil.which("inforce") is None, reason="inforce not installed on PATH")
def test_mcp_stdio_round_trip(law_pack):
    path, _ = law_pack
    names, env = asyncio.run(_mcp_round_trip(path))
    assert names == ["inforce_brief", "inforce_check", "inforce_scan"]
    assert env["verdict"] == "STALE"
    assert env["items"][0]["successorRef"] == "akn/ng/act/2025/7/sec_58"  # the whole new scale
