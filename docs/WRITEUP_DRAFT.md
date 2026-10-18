# Graders shape honesty: RL against a checklist grader vs. ground truth vs. an honesty-shaped reward

_Draft. Sections 1–4 are complete; result slots in 5 are filled from `results/summary.md` and the
training curves after the runs. The preregistration (`PREREGISTRATION.md`) fixed the hypotheses,
tests and checkpoint rule before training._

## 1. Summary (fill after results)

> We RL-train Qwen 3.5 [4B/9B] on multi-step back-office tasks under three graders: a checklist
> grader (deliverables exist + agent says done), ground-truth outcome credit, and ground truth plus a
> reward for a truthful self-report. [RESULT H1].
> [RESULT H2]. The effect [does / does not] carry over to an unseen benefits-eligibility domain and
> to Zapier's AutomationBench, and IFEval is [unchanged / changed by X pp].

## 2. Why this matters

Agents finish long tasks with a confident summary. Many training and evaluation pipelines grade that
summary or the transcript with an LLM, not the end state. If the grader can be fooled, RL will
find out how. We measure **false success** (the agent reports `completed=true` while the end
state is wrong), compare three graders on the same model, data and budget, and test whether a cheap
reward change prevents the behavior without costing real performance.

## 3. Environments

- **letter-vs-intent v0.6** (training + held-out test). 14 families of back-office work across three
  levels: collections, refunds, restocking, dedupe, month-end close with multi-currency balances,
  payroll with CA daily overtime, and legal-hold collections. Records sit behind pagination, writes
  fail transiently, and some requests are impossible or only partly possible, where the honest
  report is "not completed". Ground truth is the database and outbox end state.
- **Caseworker v0.2** (unseen domain). Batches of synthetic SNAP applications under the FFY 2026
  federal rules (income tests, deductions, shelter cap, 30% rule, minimum benefit, categorical
  eligibility) with case-file traps. Harm metrics: wrongful denials and food-aid dollars withheld.
- **AutomationBench (Zapier) + self-report** (unseen third-party benchmark). Its tasks, tools and
  state assertions are unchanged; a wrapper adds `submit_report` so false success is measurable.
- **IFEval** (capability retention).

## 4. Before training: the graders on paper

### 4.1 Which rewards pay for lying? (scripted policies, no model)

Mean reward on 70 mixed-level tasks. "Half" policies do the same half of the work and differ only
in the report.

| Policy | Outcome (partial) | Honest (honest_partial) | Report-trusting (letter) |
|---|---|---|---|
| Full work, truthful report | 1.00 | 1.00 | 0.76 |
| Half work, admits it | 0.41 | **0.58** | 0.00 |
| Half work, claims done | 0.33 | 0.23 | **1.00** |
| No work, claims done | 0.27 | 0.19 | **1.00** |

Under the honest reward, admitting failure beats claiming success by exactly 0.30 at any level of
work. Under report-trusting reward, lying is optimal. (Caveat: outcome partial credit pays some
junk writes slightly more than honest half-work on letter-vs-intent, 0.45 vs 0.41.)

### 4.2 Can an LLM judge grade these tasks at all? (100 labeled rollouts)

| Judge | Passes correct runs | Catches failed runs | Balanced accuracy |
|---|---|---|---|
| Qwen 3.5 9B, transcript | 61% | 43% | 0.52 |
| Qwen 3.5 9B, final database | 15% | 92% | 0.54 |
| Qwen 3.5 122B, transcript | 47% | 74% | 0.61 |
| Qwen 3.5 122B, final database | 0% | 100% | 0.50 |

Given the transcript, judges trust confident reports. Given the database, they can't redo the
arithmetic and fail everything. On 216 rollouts the 9B judge passed 68% of runs that falsely
claimed success, more than the 62% of runs that really succeeded. We therefore did **not** train
against an LLM judge, since RL against a near-chance grader mostly learns noise. Instead the gameable arm uses
a deterministic checklist grader.

### 4.3 The checklist grader's exploit

Writing junk into every required output and claiming success scores **1.00**, above genuinely
complete, honest work (0.93: honest agents correctly report impossible requests as not done).

## 5. Results (slots)

### 5.1 Training dynamics
_Figure: `results/plots/training_curves.png`. Per arm: the reward being optimized, ground-truth
success, false success, judge PASS and judge fooled; held-out curves every 25 steps._

### 5.2 Held-out, same domain (`lvi-test-mixed`, 42 tasks x 3)
| Model | Real success | False success | Truthful report | Checklist score |
|---|---|---|---|---|
| Base | | | | |
| checklist | | | | |
| outcome | | | | |
| honest | | | | |

H1: [ ] · H2a: [ ] · H2b: [ ] · H5: [ ]

### 5.3 Transfer (unseen)
| Model | Caseworker: false success | Caseworker: wrongful denials | AutomationBench simple: pass | AutomationBench: false success |
|---|---|---|---|---|

H3: [ ]

### 5.4 Capability (IFEval) and robustness (pressure prompts, expert level)
H4: [ ]

### 5.5 What changed in behavior
Turns, tool calls, self-check use, report length, error types; an independent external judge on each
arm's traces.

## 6. Limitations

One model size, one seed per arm (cost), 150 steps, synthetic tasks. The gameable grader is a
programmatic checklist rather than an LLM judge, because no affordable judge could grade these tasks. The honest reward needs ground truth to score the
report, so it applies where outcomes are verifiable. That is also where it is cheapest to add.

## 7. Reproduce

`docs/RUNBOOK.md`: about $25–40 of GPU time; configs are generated and schema-validated.
