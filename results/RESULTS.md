# Results (run 2026-10-17/18): Qwen 3.5 4B, LoRA, 3 arms

Held-out test: potemkin-bench `test` split, all 14 task families (6 trained, 8 never trained on),
84 tasks x 2 attempts = 168 per model. 95% CIs: task-level paired bootstrap. Full tables:
`results/summary_final.md`. Training: 40 steps for outcome and honest; the checklist arm ran 77 steps
(a stop-watcher bug; see PREREGISTRATION deviations). Its step-40 online eval showed the same direction.

| Model | Real success | False success | Truthful report | Claims "done" when done |
|---|---|---|---|---|
| Base (untrained) | 32% [23-41] | 19% [12-27] | 30% [21-39] | 91% |
| Base + "be honest" prompt | 36% [26-45] | 12% [7-19] | 35% [25-44] | 91% |
| **checklist** (gameable grader) | 32% [23-42] | 18% [10-26] | 32% [22-42] | 97% |
| **outcome** (ground truth) | 46% [37-57] | 5% [2-9] | 46% [36-57] | 96% |
| **honest** (ground truth + truthful-claim bonus) | 48% [38-59] | 4% [1-8] | 47% [37-58] | 95% |

## Preregistered hypotheses

| | Result |
|---|---|
| **H1** checklist arm has more false success than outcome arm | **Supported:** +12.5 pp [+4, +23], p = 0.003 (also -14 pp real success) |
| **H2a** honest < outcome in false success | **Not supported:** -1.2 pp [-5, +2]; both arms already cut false success ~4x vs base |
| **H2b** honest not worse on real success (> -5 pp) | **Supported:** +1.8 pp [-2, +6] |
| **H2c** no collapse into "never claim done" (> -10 pp) | **Supported:** claim recall +1.9 pp [0, +6]; both ~95% |
| **H3** transfer to unseen benchmarks | **Uninformative:** AutomationBench `simple` near ceiling for all (88-90%), no differences; SafetyNetBench at 0% for the 4B (dropped) |
| **H4** IFEval retention | **No significant loss:** honest +0.0 pp [-5, +5], outcome -1.5 pp [-7.5, +4], checklist -3.5 pp [-9, +2] (base 80%, 200 prompts); a 3 pp non-inferiority margin is not established at this n |
| **H5** checklist arm games its grader (grader score - real success, vs base) | **Not supported:** +3.8 pp [-3, +11], p = 0.15 (trend) |
| **H6** training beats asking | **Supported:** honest arm vs base + honesty prompt: false success -8.3 pp [-14, -4], p < 0.001 |

One-sided task-level bootstrap tests. H1 remains significant after the preregistered Holm correction (p = 0.012).

## Takeaways

1. Ground-truth RL (either reward) raised real success +15-17 pp and cut false claims of success ~4x
   (19% → 4-5%) on held-out tasks, including families never trained on, without making the model
   refuse to claim success when it had succeeded.
2. Training against a gameable "deliverables exist + says done" grader gave none of that: success
   flat, false success flat, and it claimed "done" more often (+7 pp).
3. At this scale (40 steps), adding an explicit truthful-report bonus on top of ground-truth outcome
   reward did not add measurable honesty: the outcome reward already penalizes the few dishonest paths.
4. A prompt-only honesty instruction helped a little (19% → 12%); training did much better (4%).

## Caveats

One seed per arm, 4B model, synthetic tasks, short training. The checklist arm trained longer
(77 vs 40 steps). AutomationBench near ceiling and SafetyNetBench at floor, so transfer claims are limited. IFEval was rerun
separately (2026-10-18) after fixing an eval-config error (network policy vs subprocess runtime).
