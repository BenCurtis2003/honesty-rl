# Runbook: from $0 to results

Every step before **4. Pilot** is free. Costs assume one node with 2x A6000 48GB at $0.54/GPU-hr
($1.08/hr), running the arms one after another. Three nodes in parallel cost the same but finish ~3x
sooner.

## 0. Free, already done locally

- Environments: potemkin-bench v0.6 (reward modes `checklist`, `partial`, `honest_partial`, `judge`, `letter`;
  `mixed` level), SafetyNetBench v0.2 (same modes). All tests pass.
- Configs: `python scripts/make_configs.py` generates `configs/`; validated against prime-rl's own
  schema with `.venv-cfg/bin/python scripts/validate_configs.py`.
- Pre-studies: `results/hackability.md`, `results/judge_cal_*.jsonl`, `results/probe/` (4B vs 9B).

## 1. Budget

| Stage (measured, 2x A6000 at $1.08/hr) | Node hours | Cost |
|---|---|---|
| Setup (with all fixes in `setup_node.sh`) | ~0.2 | ~$0.25 |
| Pilot (10 steps) | ~0.8 | ~$1 |
| One arm, 40 steps (step 40 at ~4.7 h, incl. step-0 eval) | ~4.7 | ~$5 |
| Final evals: 4 models x (84 tasks x 2 + AutomationBench 50) | ~2.5 | ~$3 |
| IFEval, 4 models x 200 prompts | ~0.4 | ~$0.50 |
| **3 arms + evals** | | **~$20** |

Step time grows as training goes on (6 min early, 16-36 min past step 60 in our runs), so budget
by measured wall-clock, not by step count.

Safety, learned the hard way:
- Run `scripts/budget_guard.sh` locally for every rented node, and still check in yourself: it stalled twice.
- After any `prime pods create`, check `prime wallet` billing rows for stray nodes. Never pipe input into
  `pods create` to see options; that silently created a second node.
- prime-rl logs contain ANSI color codes; strip them before grepping (`sed "s/\x1b\[[0-9;]*m//g"`).
- Do not export `VLLM_API_KEY`: vLLM then requires it, and the orchestrator gets 401.

Spending guards: (1) if the pilot's step time is over 3 minutes, re-plan before the full runs;
(2) the two 2nd-seed runs go last. Check `prime wallet` after the first three arms, and launch them
only if at least $12 remains (one 2nd seed needs ~$4.50 plus evals).

## 2. Get a node and copy the code

```bash
prime availability list --gpu-type A6000_48GB           # pick a 2-GPU row (~$1.08/hr), note its ID
prime pods create --id <ID> --name honesty-rl --disk-size 200
prime pods list                                         # wait for ACTIVE, note the pod ID
# copy the four project folders (no venvs, no old outputs)
for d in potemkin-bench safety-net-bench honesty-rl; do
  rsync -az --exclude '.venv*' --exclude 'outputs*' --exclude '__pycache__' \
    ~/code/$d <user>@<pod-ip>:~/
done
prime pods ssh <pod-id>
```

## 3. Set up the node (~15 min, free apart from node time)

```bash
bash ~/honesty-rl/scripts/gpu/setup_node.sh   # prime-rl @ pinned commit, envs, AutomationBench venv, offline tests
wandb login                                   # training curves
```

## 4. Pilot (~$1): go/no-go

```bash
bash ~/honesty-rl/scripts/gpu/pilot.sh
cd ~/prime-rl && uv run dashboard             # http://localhost:7788 via ssh -L 7788:localhost:7788
```

Check against PREREGISTRATION.md's go/no-go table:

1. **Tool calls parse:** step-0 eval rollouts show tool calls (dashboard → traces). If the agent
   answers in plain text, the auto parser is wrong; set `[inference.vllm] tool_call_parser`.
2. **Grader varies:** `checklist_score` and `task_success` vary across rollouts.
3. **Signal:** non-zero-advantage groups ≥ 30% (curriculum gate stats in the orchestrator log).
4. **Throughput:** ≤ 3 min per step.
5. **Stability:** errors < 10%, truncations < 20%.


## 5. Full runs (~$5 per arm)

On the same node, one after another (~20 h), or in parallel on separate nodes (same cost):

```bash
for arm in checklist outcome honest; do bash ~/honesty-rl/scripts/gpu/run_arm.sh $arm; done
prime wallet    # >= $12 left? then the 2nd seed:
for arm in outcome_s2 honest_s2; do bash ~/honesty-rl/scripts/gpu/run_arm.sh $arm; done
```

Each run ends by copying its final LoRA adapter to `~/adapters/<arm>`. Copy all three adapters
to one node for the final evals.

## 6. Final evals (~$3)

```bash
bash ~/honesty-rl/scripts/gpu/final_evals.sh base checklist outcome honest outcome_s2 honest_s2
```

This writes `results/<model>/<source>/` for six sources (lvi-test-mixed, lvi-test-expert,
lvi-pressure, lvi-honesty-prompt, caseworker-test, ifeval, plus automationbench-simple).

## 7. Analysis (local, free)

```bash
rsync -az <user>@<pod-ip>:~/honesty-rl/results/ ~/code/honesty-rl/results/
python scripts/analyze.py results --baseline base --plots --merge-seeds   # outcome_s2 pools into outcome, etc.
python scripts/training_curves.py --entity <wandb-user> --runs checklist outcome honest
# ~$0.30: would an LLM judge (Qwen 3.5 122B, transcript) catch each arm's false successes?
for m in base checklist outcome honest; do
  python scripts/judge_calibration.py results/$m/lvi-test-mixed/**/*.jsonl --judge Qwen/Qwen3.5-122B-A10B \
    --out results/judge_on_$m.jsonl
done
```

Then terminate every pod: `prime pods terminate <pod-id>`.

## 8. Release

- Push potemkin-bench v0.6 and SafetyNetBench v0.2 to the Hub (public).
- Upload the three LoRA adapters to Hugging Face with a model card linking the writeup.
- Publish `docs/WRITEUP_DRAFT.md` (filled in), the configs, and `results/summary.md`.
