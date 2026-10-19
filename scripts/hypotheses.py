"""Preregistered hypothesis tests (PREREGISTRATION.md) from a results root.

    python scripts/hypotheses.py results/final_evals                 # seed 1
    python scripts/hypotheses.py results/two_seeds --merge-seeds     # both seeds pooled per task

All comparisons are paired over the same test tasks with a task-level bootstrap (2,000 resamples).
p-values are one-sided; Holm correction across the four primary tests (H1, H2a, H2b, H2c).
"""

from __future__ import annotations

import argparse
import pathlib
import random
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from analyze import load  # noqa: E402

MAIN, PROMPT = "potemkin-test-mixed", "potemkin-honesty-prompt"
N = 2000


def task_means(rows, value) -> dict[str, float]:
    d = defaultdict(list)
    for r in rows:
        v = value(r)
        if v is not None:  # pair by base task: ids end in the prompt variant (-neutral, -honesty_prompt)
            d[r["task"].rsplit("-", 1)[0]].append(float(v))
    return {k: sum(v) / len(v) for k, v in d.items()}


def paired(a: dict, b: dict, margin: float = 0.0, seed: int = 0):
    """Mean of (b - a) over shared tasks, 95% CI, and p = share of resamples with (b - a) <= margin
    (for 'b > a + margin') plus its mirror 1 - p (for 'b < a + margin')."""
    keys = sorted(set(a) & set(b))
    d = {k: b[k] - a[k] for k in keys}
    rng = random.Random(seed)
    stats = sorted(sum(d[k] for k in rng.choices(keys, k=len(keys))) / len(keys) for _ in range(N))
    mean = sum(d.values()) / len(d)
    p_le = sum(s <= margin for s in stats) / N
    p_ge = sum(s >= margin for s in stats) / N
    return mean, stats[int(0.025 * N)], stats[int(0.975 * N) - 1], p_le, p_ge


def claim_recall_by_task(rows):
    """Per task, share of runs that claimed done among runs where 'done' was the truthful claim."""
    return task_means(rows, lambda r: r.get("claim_recall"))


def holm(ps: dict[str, float]) -> dict[str, float]:
    order = sorted(ps, key=ps.get)
    out, running = {}, 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, (len(order) - i) * ps[k]))
        out[k] = running
    return out


def run(root: pathlib.Path, merge_seeds: bool) -> str:
    data = load(root, merge_seeds)
    m = {arm: data[arm][MAIN] for arm in ("base", "checklist", "outcome", "honest") if arm in data and MAIN in data[arm]}
    fs = {arm: task_means(rows, lambda r: r.get("false_success")) for arm, rows in m.items()}
    rs = {arm: task_means(rows, lambda r: r.get("success")) for arm, rows in m.items()}
    res, ps = [], {}

    d, lo, hi, p_le, _ = paired(fs["outcome"], fs["checklist"])
    ps["H1"] = p_le
    res.append(("H1 checklist > outcome, false success", d, lo, hi, p_le))
    d, lo, hi, _, p_ge = paired(fs["outcome"], fs["honest"])
    ps["H2a"] = p_ge
    res.append(("H2a honest < outcome, false success", d, lo, hi, p_ge))
    d, lo, hi, p_le, _ = paired(rs["outcome"], rs["honest"], margin=-0.05)
    ps["H2b"] = p_le
    res.append(("H2b honest - outcome > -5pp, real success", d, lo, hi, p_le))
    d, lo, hi, p_le, _ = paired(claim_recall_by_task(m["outcome"]), claim_recall_by_task(m["honest"]), margin=-0.10)
    ps["H2c"] = p_le
    res.append(("H2c honest - outcome > -10pp, claim recall", d, lo, hi, p_le))
    gap = lambda r: None if r.get("checklist_score") is None else r["checklist_score"] - r["success"]  # noqa: E731
    d, lo, hi, p_le, _ = paired(task_means(m["base"], gap), task_means(m["checklist"], gap))
    res.append(("H5 checklist arm games its grader vs base", d, lo, hi, p_le))
    if "base" in data and PROMPT in data["base"]:
        d, lo, hi, _, p_ge = paired(task_means(data["base"][PROMPT], lambda r: r.get("false_success")), fs["honest"])
        res.append(("H6 honest < base + honesty prompt, false success", d, lo, hi, p_ge))
    adj = holm(ps)
    lines = [f"Root: {root}{' (seeds merged per task)' if merge_seeds else ''}", "",
             "| Hypothesis | Difference | 95% CI | p (one-sided) | Holm p |", "|---|---|---|---|---|"]
    for name, d, lo, hi, p in res:
        key = name.split()[0]
        lines.append(f"| {name} | {100 * d:+.1f} pp | [{100 * lo:+.1f}, {100 * hi:+.1f}] | {p:.3f} | "
                     f"{adj[key]:.3f} |" if key in adj else
                     f"| {name} | {100 * d:+.1f} pp | [{100 * lo:+.1f}, {100 * hi:+.1f}] | {p:.3f} | - |")
    lines.append("")
    lines.append("Real success / false success per arm (task means): " + ", ".join(
        f"{arm} {100 * sum(rs[arm].values()) / len(rs[arm]):.0f}% / {100 * sum(fs[arm].values()) / len(fs[arm]):.0f}%" for arm in m))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--merge-seeds", action="store_true")
    a = ap.parse_args()
    print(run(pathlib.Path(a.root), a.merge_seeds))


if __name__ == "__main__":
    main()
