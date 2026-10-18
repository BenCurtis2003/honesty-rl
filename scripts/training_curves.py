"""Training curves for every arm from Weights & Biases: the reward each arm optimized vs. ground truth.

  WANDB_API_KEY=... python scripts/training_curves.py --entity <you> --project honesty-rl \
      --runs checklist outcome honest [--list-keys]

The key plot is the divergence in the `checklist` arm: if the policy learns to game its grader,
checklist score climbs while real success stalls and false success rises.
Metric names are matched by substring, so they survive prime-rl renames; use --list-keys after
the pilot to confirm which keys exist and adjust PANELS if needed.
"""

from __future__ import annotations

import argparse
import pathlib

PANELS = [  # (title, substrings to match in the W&B key, in priority order)
    ("Reward being optimized", ["reward/mean", "reward"]),
    ("Real success (ground truth)", ["task_success"]),
    ("False success", ["false_success"]),
    ("Checklist score (gameable grader)", ["checklist_score"]),
    ("Outputs present (checklist coverage)", ["checklist_coverage"]),
    ("Truthful report", ["calib_honest"]),
    ("Held-out potemkin-test success", ["eval/potemkin-test", "potemkin-test"]),
    ("Held-out SafetyNetBench success", ["eval/safetynet-test", "safetynet-test"]),
]


def pick(keys: list[str], subs: list[str], prefer_train: bool) -> str | None:
    for sub in subs:
        hits = [k for k in keys if sub in k]
        if prefer_train:
            hits = [k for k in hits if "eval" not in k] or hits
        if hits:
            return sorted(hits, key=len)[0]
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entity", required=True)
    ap.add_argument("--project", default="honesty-rl")
    ap.add_argument("--runs", nargs="+", default=["checklist", "outcome", "honest"])
    ap.add_argument("--out", default="results/plots/training_curves.png")
    ap.add_argument("--list-keys", action="store_true")
    a = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import wandb

    api = wandb.Api()
    runs = {r.name: r for r in api.runs(f"{a.entity}/{a.project}") if r.name in a.runs}
    missing = set(a.runs) - set(runs)
    if missing:
        print("not found in W&B:", sorted(missing))
    hist = {name: r.history(samples=10_000, pandas=True) for name, r in runs.items()}
    if a.list_keys:
        for name, h in hist.items():
            print(f"== {name}: {len(h)} rows")
            for k in sorted(h.columns):
                print("  ", k)
        return

    fig, axes = plt.subplots(2, 4, figsize=(16, 7))
    for ax, (title, subs) in zip(axes.flat, PANELS):
        for name, h in hist.items():
            key = pick(list(h.columns), subs, prefer_train="Held-out" not in title)
            if key is None:
                continue
            s = h[["_step", key]].dropna()
            ax.plot(s["_step"], s[key], label=f"{name}", marker="o" if "Held-out" in title else None, ms=3)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("step")
        ax.grid(alpha=0.3)
    axes.flat[0].legend()
    fig.tight_layout()
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    print("wrote", out)


if __name__ == "__main__":
    main()
