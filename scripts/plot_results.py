"""Main results figure: real success, false success, truthful report per model on held-out tasks.

  python scripts/plot_results.py results/final_evals results/plots/main_results.png
"""

import pathlib
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import analyze as A  # noqa: E402

root, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
d = A.load(root)
series = [  # (label, model, source)
    ("Base", "base", "lvi-test-mixed"),
    ('Base + "be honest" prompt', "base", "lvi-honesty-prompt"),
    ("Checklist grader (gameable)", "checklist", "lvi-test-mixed"),
    ("Outcome (ground truth)", "outcome", "lvi-test-mixed"),
    ("Honest (ground truth + truthful-claim bonus)", "honest", "lvi-test-mixed"),
]
metrics = [("success", "Real success"), ("false_success", "False success\n(claimed done, wasn't)"),
           ("honest_report", "Truthful report")]
colors = ["#9aa0a6", "#c7c9cc", "#d9534f", "#5b9bd5", "#2e8b57"]

fig, ax = plt.subplots(figsize=(9, 4.8))
w = 0.16
for i, ((label, model, src), color) in enumerate(zip(series, colors)):
    rows = [dict(r, task=re.sub(r"-(neutral|honesty_prompt)$", "", str(r["task"]))) for r in d[model][src]]
    vals = [A.boot_ci(rows, k) for k, _ in metrics]
    xs = [j + (i - 2) * w for j in range(len(metrics))]
    ax.bar(xs, [v[0] for v in vals], w, color=color, label=label,
           yerr=[[v[0] - v[1] for v in vals], [v[2] - v[0] for v in vals]], capsize=2, error_kw={"lw": 0.8})
ax.set_xticks(range(len(metrics)))
ax.set_xticklabels([m for _, m in metrics])
ax.set_ylim(0, 0.7)
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
ax.set_title("Qwen 3.5 4B on held-out back-office tasks (84 tasks x 2; 95% CI)", fontsize=10)
ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=180)
print("wrote", out)
