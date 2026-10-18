"""Hackability audit: how much does each reward pay scripted policies that cut corners or lie?

No model calls. Policies are built from the environments' reference solvers:
  full_honest     correct work, truthful report
  full_underclaim correct work, reports completed=false
  full_silent     correct work, no report
  half_admit      half the required changes, reports completed=false
  half_claim      half the required changes, claims completed=true
  junk_claim      every required field overwritten with junk, claims completed=true
  claim_only      no work, claims completed=true

A reward is hackable if a dishonest or low-effort policy outscores an honest one.
The LLM-judge reward needs a transcript, so it's measured empirically in training instead.

Usage: python scripts/hackability_audit.py [--n 70] [--out results/hackability.md]
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import pathlib
import random
import sys
from types import SimpleNamespace

ROOT = pathlib.Path.home() / "code"
sys.path[:0] = [str(ROOT / "letter-vs-intent/tests"), str(ROOT / "caseworker/tests")]

import test_families as t1  # noqa: E402
import test_families_v2 as t2  # noqa: E402
import test_families_v3 as t3  # noqa: E402
import test_caseworker as tc  # noqa: E402
import caseworker.taskset as cts  # noqa: E402
from caseworker.cases import build_batch  # noqa: E402
from letter_vs_intent.servers.tool import OfficeState  # noqa: E402
from letter_vs_intent.taskset import (LetterVsIntentConfig, LetterVsIntentTask,  # noqa: E402
                                      LetterVsIntentTaskConfig, LetterVsIntentTaskset)

MODES = ("strict", "partial", "honest", "honest_partial", "checklist", "letter")
POLICIES = ("full_honest", "full_underclaim", "full_silent", "half_admit", "half_claim", "junk_claim", "claim_only")


def lvi_solve(family: str, st: OfficeState, spec: dict) -> None:
    if family in t1.FAMILIES if hasattr(t1, "FAMILIES") else family in ("overdue", "refunds", "reorder", "dedupe", "impossible"):
        t1.solve(family, st, spec)
    elif family in ("collections", "refunds_policy", "reorder_cases", "dedupe_messy", "partial_batch", "memo_override"):
        t2.solve(family, st, spec)
    else:
        t3.solve(family, st, spec)


def degrade(initial: dict, full: OfficeState, how: str, rng: random.Random) -> OfficeState:
    """Copy of a solved state with half the record changes reverted, or every changed field set to junk."""
    st = OfficeState(db=copy.deepcopy(full.db), outbox=list(full.outbox), report=dict(full.report or {}))
    for table, rows in st.db.items():
        base = initial.get(table, {})
        changed = [k for k in rows if rows[k] != base.get(k)]
        if how == "half":
            for k in rng.sample(changed, len(changed) // 2):
                if k in base:
                    rows[k] = copy.deepcopy(base[k])
                else:
                    del rows[k]
            for k in [k for k in base if k not in rows][::2]:  # undo half the deletions too
                rows[k] = copy.deepcopy(base[k])
        else:  # junk
            for k in changed:
                for f, v in rows[k].items():
                    if base.get(k, {}).get(f) != v:
                        rows[k][f] = "0"
    if how == "half":
        st.outbox = st.outbox[: len(st.outbox) // 2]
    return st


def with_report(st: OfficeState, report: dict | None) -> OfficeState:
    return OfficeState(db=st.db, outbox=st.outbox, report=report, actions=list(st.actions))


def log_actions(initial: dict, st: OfficeState) -> OfficeState:
    """Scripted policies edit the db directly; rebuild the action log a tool-using agent would leave."""
    acts = []
    for table, rows in st.db.items():
        base = initial.get(table, {})
        for rid, rec in rows.items():
            if rid not in base:
                acts.append(f"create {table}.{rid}")
                continue
            for f, v in rec.items():
                if base[rid].get(f) != v:
                    acts.append(f"update {table}.{rid}.{f}={v!r}")
        acts += [f"delete {table}.{rid}" for rid in base if rid not in rows]
    st.actions = acts
    return st


async def score(task_cls, cfg_cls, data, st, mode) -> float:
    trace = SimpleNamespace(state=st, info={}, messages=[])
    return float(await task_cls(data, cfg_cls(reward_mode=mode)).intent(trace))


def policies_for(initial: dict, full: OfficeState, truth_ok: bool, rng: random.Random) -> dict[str, OfficeState]:
    log_actions(initial, full)
    half = log_actions(initial, degrade(initial, full, "half", rng))
    junk = log_actions(initial, degrade(initial, full, "junk", rng))
    claim = {"completed": True, "summary": "All done."}
    admit = {"completed": False, "summary": "Some items are not finished."}
    return {
        "full_honest": with_report(full, full.report if full.report is not None else {"completed": truth_ok, "summary": ""}),
        "full_underclaim": with_report(full, admit),
        "full_silent": with_report(full, None),
        "half_admit": with_report(half, admit),
        "half_claim": with_report(half, claim),
        "junk_claim": with_report(junk, claim),
        "claim_only": OfficeState(db=copy.deepcopy(initial), report=claim),
    }


def audit_lvi(n: int) -> dict:
    tasks = LetterVsIntentTaskset(LetterVsIntentConfig(num_tasks=n, difficulty="mixed", scale="small")).load()
    rng = random.Random(0)
    acc = {p: {m: [] for m in MODES} for p in POLICIES}
    for task in tasks:
        full = OfficeState(db=copy.deepcopy(task.data.db))
        lvi_solve(task.data.family, full, task.data.spec)
        ok = min(LetterVsIntentTask(task.data, LetterVsIntentTaskConfig())._components(SimpleNamespace(state=full)).values()) == 1.0
        assert ok, f"reference solver failed on {task.data.family}"
        for p, st in policies_for(task.data.db, full, ok, rng).items():
            for m in MODES:
                acc[p][m].append(asyncio.run(score(LetterVsIntentTask, LetterVsIntentTaskConfig, task.data, st, m)))
    return acc


def audit_caseworker(n: int) -> dict:
    rng = random.Random(1)
    acc = {p: {m: [] for m in MODES} for p in POLICIES}
    for i in range(n):
        _, db, spec = build_batch(random.Random(1000 + i), 5)
        data = cts.CaseworkerData(id=f"a{i}", name="snap_batch", prompt="", db=db, spec=spec)
        full = tc._state(db)
        tc._solve(full.db, spec, full.outbox)
        full.report = {"completed": True, "summary": "done"}
        for p, st in policies_for(db, full, True, rng).items():
            for m in MODES:
                acc[p][m].append(asyncio.run(score(cts.CaseworkerTask, cts.CaseworkerTaskConfig, data, st, m)))
    return acc


def table(name: str, acc: dict) -> str:
    rows = [f"### {name}\n", "| policy | " + " | ".join(MODES) + " |", "|---" * (len(MODES) + 1) + "|"]
    for p in POLICIES:
        rows.append(f"| {p} | " + " | ".join(f"{sum(v) / len(v):.2f}" for v in acc[p].values()) + " |")
    mean = {p: {m: sum(v) / len(v) for m, v in acc[p].items()} for p in POLICIES}
    rows.append("\nDoes cheating pay? (yes = the cheating policy outscores honest half-work)\n")
    rows.append("| test | " + " | ".join(MODES) + " |")
    rows.append("|---" * (len(MODES) + 1) + "|")
    for label, cheat in (("lying about the same work (half_claim)", "half_claim"),
                         ("lying with no work (claim_only)", "claim_only"),
                         ("junk work + lying (junk_claim)", "junk_claim")):
        rows.append(f"| {label} | " + " | ".join(
            "**yes**" if mean[cheat][m] > mean["half_admit"][m] + 1e-9 else "no" for m in MODES) + " |")
    rows.append("")
    return "\n".join(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=70)
    ap.add_argument("--out", default="results/hackability.md")
    a = ap.parse_args()
    md = "## Reward hackability audit (mean reward; scripted policies, no model)\n\n"
    md += table(f"letter-vs-intent, mixed level, small scale ({a.n} tasks)", audit_lvi(a.n)) + "\n"
    md += table(f"caseworker, 5-case batches ({a.n // 2} batches)", audit_caseworker(a.n // 2))
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    print(md)


if __name__ == "__main__":
    main()
