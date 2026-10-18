"""Compare models (base vs. each trained arm) across every eval source, with task-level bootstrap CIs.

  python scripts/analyze.py results/            # walks results/<model>/<source>/**/traces.jsonl (v1)
                                                #   and results/<model>/automationbench/**/results.jsonl (v0)
  python scripts/analyze.py results/ --baseline base --plots

Outputs results/summary.md (tables) and, with --plots, results/plots/*.png.
Paired comparisons resample the SAME tasks for both models, so task difficulty cancels out.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
from collections import defaultdict

METRICS = {  # name -> (label, higher_is_better)
    "success": ("Real success", True),
    "partial": ("Partial credit", True),
    "claimed": ("Claimed done", None),
    "false_success": ("False success", False),
    "honest_report": ("Truthful report", True),
    "claim_recall": ("Claims done when done", True),
    "checklist_score": ("Checklist grader", None),
    "judge_pass": ("Judge PASS", None),
    "judge_fooled": ("Judge fooled", False),
    "check_tool_used": ("Used check tool", None),
    "wrongful_denial_rate": ("Wrongful denials / case", False),
    "benefit_withheld_per_case": ("$ withheld / case", False),
}


def _lines(path: pathlib.Path):
    """Text lines of a .jsonl or zstd-compressed .jsonl.zst file (prime-rl's trace stream)."""
    if path.suffix == ".zst":
        import io
        import zstandard
        with open(path, "rb") as fh:
            yield from io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(fh), encoding="utf-8")
    else:
        yield from open(path)


def _v1_rows(path: pathlib.Path) -> list[dict]:
    rows = []
    for line in _lines(path):
        if not line.strip():
            continue
        e = json.loads(line)
        data = (e.get("task") or {}).get("data") or {}
        for t in e.get("traces", []):
            if t.get("errors"):
                continue
            m = t.get("metrics") or {}
            r = (t.get("rewards") or {})
            reward = next((v.get("score") for v in r.values() if isinstance(v, dict)), None)
            succ = m.get("task_success", reward if reward in (0.0, 1.0) else None)
            row = {"task": data.get("id") or data.get("idx"), "success": succ,
                   "partial": m.get("partial_score", reward), "claimed": m.get("letter"),
                   "false_success": m.get("false_success"), "honest_report": m.get("calib_honest"),
                   "reward": reward,
                   # guards against 'always say not done': only defined when a done-claim was warranted
                   "claim_recall": m.get("letter") if m.get("calib_should_claim") == 1.0 else None}
            for k in ("checklist_score", "judge_pass", "judge_fooled", "check_tool_used", "wrongful_denial_rate",
                      "benefit_withheld_per_case"):
                if k in m:
                    row[k] = m[k]
            msgs = [n.get("message") or {} for n in t.get("nodes", [])]
            row["turns"] = sum(1 for x in msgs if x.get("role") == "assistant")
            row["tool_calls"] = sum(len(x.get("tool_calls") or []) for x in msgs if x.get("role") == "assistant")
            rep = ((t.get("info") or {}).get("final_state") or {}).get("report") or {}
            row["report_words"] = len(str(rep.get("summary", "")).split()) if rep else 0
            row["checked_after_last_write"] = m.get("checked_after_last_write")
            rows.append(row)
    return rows


def _v0_rows(path: pathlib.Path) -> list[dict]:
    """vf-eval (v0) results.jsonl: one row per rollout with metric columns."""
    rows = []
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        rows.append({"task": r.get("example_id", r.get("id")), "success": r.get("task_completed_correctly"),
                     "partial": r.get("partial_credit", r.get("reward")), "claimed": r.get("claimed"),
                     "false_success": r.get("false_success"), "honest_report": r.get("honest_report"),
                     "reward": r.get("reward")})
    return rows


def _sniff(path: pathlib.Path) -> str | None:
    """'v1' for episode records (vf-eval v1 / prime-rl trace stream), 'v0' for vf-eval v0 rollouts."""
    first = next(iter(_lines(path)), "")
    try:
        rec = json.loads(first)
    except json.JSONDecodeError:
        return None
    if isinstance(rec, dict) and "traces" in rec and "task" in rec:
        return "v1"
    if isinstance(rec, dict) and ("task_completed_correctly" in rec or ("reward" in rec and "example_id" in rec)):
        return "v0"
    return None


def load(root: pathlib.Path, merge_seeds: bool = False) -> dict[str, dict[str, list[dict]]]:
    """{model: {source: rows}} from results/<model>/<source>/...
    With merge_seeds, `<arm>_s2` rows join `<arm>`: per-task means then average over both seeds."""
    out: dict[str, dict[str, list[dict]]] = defaultdict(dict)
    for model_dir in sorted(p for p in root.iterdir() if p.is_dir() and p.name != "plots"):
        name = re.sub(r"_s\d+$", "", model_dir.name) if merge_seeds else model_dir.name
        for src_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
            rows = []
            for f in sorted([*src_dir.rglob("*.jsonl"), *src_dir.rglob("*.jsonl.zst")]):
                if "/live/" in str(f) or "/annotations/" in str(f) or f.name in ("metrics.jsonl", "plan.jsonl", "stream.index.jsonl"):
                    continue
                kind = _sniff(f)
                rows += _v1_rows(f) if kind == "v1" else _v0_rows(f) if kind == "v0" else []
            if rows:
                out[name].setdefault(src_dir.name, []).extend(rows)
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def by_task(rows, metric):
    d = defaultdict(list)
    for r in rows:
        if r.get(metric) is not None:
            d[r["task"]].append(float(r[metric]))
    return {k: sum(v) / len(v) for k, v in d.items()}


def boot_ci(rows, metric, n=2000, seed=0):
    t = by_task(rows, metric)
    if not t:
        return float("nan"), float("nan"), float("nan")
    keys, rng = list(t), random.Random(seed)
    stats = sorted(sum(t[k] for k in rng.choices(keys, k=len(keys))) / len(keys) for _ in range(n))
    return sum(t.values()) / len(t), stats[int(0.025 * n)], stats[int(0.975 * n) - 1]


def paired_diff(rows_a, rows_b, metric, n=2000, seed=0):
    """Mean of (B - A) over tasks both models ran, with a paired bootstrap CI and the share of
    resamples where the difference is <= 0 (a one-sided p-value for 'B > A')."""
    a, b = by_task(rows_a, metric), by_task(rows_b, metric)
    keys = sorted(set(a) & set(b))
    if len(keys) < 2:
        return float("nan"), float("nan"), float("nan"), float("nan")
    d = {k: b[k] - a[k] for k in keys}
    rng = random.Random(seed)
    stats = sorted(sum(d[k] for k in rng.choices(keys, k=len(keys))) / len(keys) for _ in range(n))
    p_le0 = sum(s <= 0 for s in stats) / n
    return sum(d.values()) / len(d), stats[int(0.025 * n)], stats[int(0.975 * n) - 1], p_le0


def pct(x):
    return "-" if x != x else f"{100 * x:.0f}%"


def fmt_ci(t, money=False):
    p, lo, hi = t
    if p != p:
        return "-"
    if money:
        return f"${p:.0f} [{lo:.0f}-{hi:.0f}]"
    return f"{100 * p:.0f}% [{100 * lo:.0f}-{100 * hi:.0f}]"


def report(data, baseline: str | None) -> str:
    models = sorted(data, key=lambda m: (m != baseline, m))
    sources = sorted({s for m in data.values() for s in m})
    md = ["# Results\n", "95% CIs resample tasks (all rollouts of a task move together).\n"]
    for src in sources:
        md.append(f"\n## {src}\n")
        present = [k for k in METRICS if any(any(r.get(k) is not None for r in data[m].get(src, [])) for m in models)]
        md.append("| model | n | " + " | ".join(METRICS[k][0] for k in present) + " |")
        md.append("|---|---|" + "---|" * len(present))
        for m in models:
            rows = data[m].get(src)
            if not rows:
                continue
            cells = [fmt_ci(boot_ci(rows, k), money=k.endswith("per_case") and "benefit" in k) for k in present]
            md.append(f"| {m} | {len(rows)} | " + " | ".join(cells) + " |")
        if baseline and baseline in data and src in data[baseline]:
            md.append(f"\nChange vs `{baseline}` (paired over shared tasks; p = share of resamples with no improvement):\n")
            md.append("| model | " + " | ".join(METRICS[k][0] for k in present) + " |")
            md.append("|---|" + "---|" * len(present))
            for m in models:
                if m == baseline or src not in data[m]:
                    continue
                cells = []
                for k in present:
                    d, lo, hi, p = paired_diff(data[baseline][src], data[m][src], k)
                    good = METRICS[k][1]
                    pval = p if good is True else (1 - p if good is False else None)
                    star = "" if pval is None or pval != pval else (" *" if pval < 0.05 else "")
                    cells.append("-" if d != d else f"{100 * d:+.0f}pp [{100 * lo:+.0f}, {100 * hi:+.0f}]{star}")
                md.append(f"| {m} | " + " | ".join(cells) + " |")
    md.append("\n`*` = improvement in the good direction with one-sided bootstrap p < 0.05.\n")
    md.append("\n## Behavior (means per rollout)\n")
    md.append("| model | source | turns | tool calls | report words | checked after last write |")
    md.append("|---|---|---|---|---|---|")
    for src in sources:
        for m in models:
            rows = data[m].get(src)
            if not rows or not any("turns" in r for r in rows):
                continue
            chk = mean([r.get("checked_after_last_write") for r in rows])
            md.append(f"| {m} | {src} | {mean([r.get('turns') for r in rows]):.1f} | "
                      f"{mean([r.get('tool_calls') for r in rows]):.1f} | {mean([r.get('report_words') for r in rows]):.0f} | {pct(chk)} |")
    return "\n".join(md)


def plots(data, out: pathlib.Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out.mkdir(parents=True, exist_ok=True)
    models = sorted(data)
    for src in sorted({s for m in data.values() for s in m}):
        fig, ax = plt.subplots(figsize=(7, 3.6))
        metrics = [k for k in ("success", "false_success", "honest_report", "judge_fooled")
                   if any(any(r.get(k) is not None for r in data[m].get(src, [])) for m in models)]
        w = 0.8 / max(len(models), 1)
        for i, m in enumerate(models):
            vals = [boot_ci(data[m].get(src, []), k) for k in metrics]
            ax.bar([j + i * w for j in range(len(metrics))], [v[0] for v in vals], w,
                   yerr=[[v[0] - v[1] for v in vals], [v[2] - v[0] for v in vals]], label=m, capsize=2)
        ax.set_xticks([j + w * (len(models) - 1) / 2 for j in range(len(metrics))])
        ax.set_xticklabels([METRICS[k][0] for k in metrics])
        ax.set_ylim(0, 1)
        ax.set_title(src)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(out / f"{src}.png", dpi=150)
        plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--baseline", default="base")
    ap.add_argument("--plots", action="store_true")
    ap.add_argument("--merge-seeds", action="store_true", help="pool <arm>_s2 into <arm>")
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    data = load(root, a.merge_seeds)
    md = report(data, a.baseline if a.baseline in data else None)
    (root / "summary.md").write_text(md)
    print(md)
    if a.plots:
        plots(data, root / "plots")


if __name__ == "__main__":
    main()
