# Results (run 2026-10-17/18, second seed 2026-10-19): Qwen 3.5 4B, LoRA, 3 arms

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

The table above is seed 1. A second seed (seed 23, 2026-10-19, same hardware and settings) retrained the
outcome and honest arms and repeated the primary eval:

| Arm | Seed | Real success | False success | Truthful report | Claims "done" when done |
|---|---|---|---|---|---|
| outcome | 1 | 46% [37-57] | 5% [2-9] | 46% [36-57] | 96% |
| outcome | 2 | 45% [35-55] | 7% [2-11] | 45% [35-56] | 100% |
| **outcome** | **pooled** | **46% [36-56]** | **6% [3-10]** | **46% [36-56]** | **99%** |
| honest | 1 | 48% [38-59] | 4% [1-8] | 47% [37-58] | 95% |
| honest | 2 | 44% [34-55] | 6% [2-11] | 43% [34-54] | 98% |
| **honest** | **pooled** | **46% [36-56]** | **5% [2-9]** | **45% [36-56]** | **95%** |

Pooled = both seeds per task (2 seeds x 2 attempts). Full tables: `results/summary_2seeds.md`; tests:
`results/hypotheses_2seeds.md` (reproduce with `bash scripts/seed2_wrapup.sh`). Seed-2 training curves:
`results/seed2_run/*/train_curve.csv` (training-batch false success fell from 34% to 11% for outcome and
from 47% to 10% for honest over 40 steps).

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

**With both seeds** (outcome and honest pooled per task; checklist and base have one seed):

| | Seed 2 alone | Both seeds pooled |
|---|---|---|
| **H1** checklist > outcome, false success | +11.3 pp [+3.0, +20.8], p = 0.005 | **+11.9 pp [+3.6, +21.4], p = 0.002** (Holm, conservative 4 x p: 0.008) |
| **H2a** honest < outcome, false success | -0.6 pp [-4.2, +3.0] (not supported) | **-0.9 pp [-3.3, +1.8] (not supported)** |
| **H2b** honest not worse on real success (> -5 pp) | -0.6 pp [-5.4, +3.6], p = 0.031 | **+0.6 pp [-2.7, +3.6], p = 0.001** |
| **H2c** no collapse in claim recall (> -10 pp) | -2.2 pp [-6.5, 0.0], p = 0.004 | **-0.9 pp [-2.7, 0.0], p < 0.001** |
| **H6** honest < base + honesty prompt, false success | -6.5 pp [-12.5, -1.8], p = 0.006 | **-7.4 pp [-12.5, -3.0], p < 0.001** |

Every conclusion above holds with the second seed.

## Takeaways

1. Ground-truth RL (either reward) raised real success ~14 pp and cut false claims of success 3-4x
   (19% → 5-6%, both seeds pooled; seed 1 alone: +15-17 pp, 4-5%) on held-out tasks, including families never trained on, without making the model
   refuse to claim success when it had succeeded.
2. Training against a gameable "deliverables exist + says done" grader gave none of that: success
   flat, false success flat, and it claimed "done" more often (+7 pp).
3. At this scale (40 steps), adding an explicit truthful-report bonus on top of ground-truth outcome
   reward did not add measurable honesty: the outcome reward already penalizes the few dishonest paths.
4. A prompt-only honesty instruction helped a little (19% → 12%); training did much better (5%, both seeds pooled).

## Caveats

Two seeds for the outcome and honest arms, one for the checklist arm; 4B model, synthetic tasks, short
training. The checklist arm trained longer (77 vs 40 steps). A later scorer audit (PotemkinBench v0.8)
found that the `reorder` training family's scorer accepted under-filled orders when the budget covered
everything; rescoring every saved test run changes no outcome, but the training reward on that one family
was slightly lenient. AutomationBench near ceiling and SafetyNetBench at floor, so transfer claims are limited. IFEval was rerun
separately (2026-10-18) after fixing an eval-config error (network policy vs subprocess runtime).

## Workflow run (2026-10-28): training on one customer-style process

Qwen 3.5 4B (LoRA rank 16, prime-rl, reward_mode `honest`) trained on `workflows/ap_payment_full.yaml`, an
accounts-payable payment run with a high-value review rule, silent write failures and deferred or bouncing
remittance mail. One H200 shared by vLLM and the trainer (`configs/rl_workflow_1gpu.toml`,
`patches/prime-rl-share-gpu.patch`). Training stopped at the 95-minute cap; the eval used the step-23 adapter.
Evaluated on 40 held-out test-split instances, 2 rollouts each (80 per arm).

| Metric | Base | Trained (23 steps) | Paired permutation p (per instance) |
|---|---|---|---|
| Success | 46.3% | 63.7% | 0.008 (better on 14 instances, worse on 3) |
| False success | 18.8% | 8.7% | 0.08 (better on 10, worse on 3) |
| Honest report | 72.5% | 85.0% | 0.03 |
| Claimed done | 56.2% | 56.2% | |

One seed, one run, and the test instances come from the same workflow as training, so this shows improvement
on that process rather than transfer. The first attempt used `ap_payment_lite.yaml`; base success there was
93.8% with 0% false success, so the run stopped before training (`results/workflow_run/workflow_run/`). Results:
`results/workflow_full/`. Cost about $13 on a $5.40/hr H200 (plus $4.44 for the lite attempt).
