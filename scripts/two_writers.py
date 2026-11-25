"""Two writers, one project graph: a scanner and an agent.

A `.rl` store has one writer at a time; a second opener gets "storage locked"
(exit 5). InForce opens per command and retries with backoff, so a scanner and
an agent can share demo/naira-payroll/.inforce/project.rl. This script makes the
collision happen on purpose and prints the retry log.

  Writer 1 (scanner): holds the project graph for 0.8 s. A real scan of the demo
                      takes milliseconds, so the hold SIMULATES a long scan of a big repo.
  Writer 2 (agent):   `inforce check <answer> --record <repo>` while writer 1 holds it:
                      it logs its retries, then records the answer.
  Then a real `inforce scan` runs and lists the agent's answer beside the code.

Runs on a temporary copy of the demo repo unless --in-place is given.
Usage: python scripts/two_writers.py [--in-place]
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo" / "naira-payroll"
INFORCE = shutil.which("inforce") or "inforce"

HOLDER = """
import sys, time
from inforce.store import open_store
with open_store(sys.argv[1]) as s:
    s.execute("RETURN 1 AS ok")
    print("held", flush=True)
    time.sleep(float(sys.argv[2]))
print("released", flush=True)
"""


def main() -> int:
    if "--in-place" in sys.argv:
        repo = DEMO
    else:
        repo = Path(tempfile.mkdtemp(prefix="inforce-two-writers-")) / "naira-payroll"
        shutil.copytree(DEMO, repo, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    store = repo / ".inforce" / "project.rl"
    if not store.exists():
        subprocess.run([INFORCE, "scan", str(repo)], capture_output=True, check=False)
    t0 = time.monotonic()
    stamp = lambda: f"[{time.monotonic() - t0:5.2f}s]"  # noqa: E731

    print(f"{stamp()} writer 1 (scanner, simulated long scan) opens {store}")
    holder = subprocess.Popen([sys.executable, "-c", HOLDER, str(store), "0.8"], stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == "held"
    print(f"{stamp()} writer 1 holds the write lock")

    answer = DEMO / "answers" / "stale_answer.md"
    print(f"{stamp()} writer 2 (agent) records an answer: inforce check {answer.name} --record ...")
    agent = subprocess.Popen([INFORCE, "check", str(answer), "--record", str(repo), "--id", "chat-2025-07",
                              "--json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in agent.stderr:  # live: each retry appears as it happens
        print(f"{stamp()}   agent log: {line.strip()}")
    agent.stdout_text = agent.stdout.read()
    agent.wait()
    holder.wait()
    print(f"{stamp()} writer 1 released the lock")
    recorded = '"recorded"' in agent.stdout_text
    print(f"{stamp()} writer 2 finished: exit {agent.returncode} (3 = answer rests on repealed law), "
          f"recorded={recorded}")

    scan = subprocess.run([INFORCE, "scan", str(repo), "--json"], capture_output=True, text=True)
    import json
    rep = json.loads(scan.stdout)
    agent_art = [a for a in rep["artifacts"] if a["id"] == "agent/chat-2025-07"]
    print(f"{stamp()} real scan: {sum(a['status'] == 'STALE' for a in rep['artifacts'])} STALE artifacts; "
          f"agent answer kept: {agent_art[0]['status'] if agent_art else 'MISSING'}")
    print(f"store: {store}")
    return 0 if recorded and agent_art else 1


if __name__ == "__main__":
    raise SystemExit(main())
