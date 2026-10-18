# Runbook: from $0 to results

Every step before **4. Pilot** is free. Costs assume one node with 2x A6000 48GB at $0.54/GPU-hr
($1.08/hr), running the arms one after another. Three nodes in parallel cost the same but finish ~3x
sooner.

## 0. Free, already done locally

- Environments: letter-vs-intent v0.6 (reward modes `checklist`, `partial`, `honest_partial`, `judge`, `letter`;
  `mixed` level), Caseworker v0.2 (same modes). All tests pass.
- Configs: `python scripts/make_configs.py` generates `configs/`; validated against prime-rl's own
  schema with `.venv-cfg/bin/python scripts/validate_configs.py`.
- Pre-studies: `results/hackability.md`, `results/judge_cal_*.jsonl`, `results/probe/` (4B vs 9B).

## 1. Budget

| Stage | Node hours | Cost |
|---|---|---|
| Setup + pilot (20 steps) | ~1.5 | ~$2 |
| checklist, outcome, honest (150 steps each, 30-turn cap) | ~4 each | ~$13 |
| 2nd seed: outcome_s2, honest_s2 (run last) | ~4 each | ~$9 |
| Final evals (2nd seeds: primary sources only) + AutomationBench simple | ~3 | ~$3 |
| Does an LLM judge catch the cheating? (API, 122B) | - | ~$0.30 |
| **Expected total** | | **~$27** (fits $30 with ~$3 spare) |

Spending guards: (1) if the pilot's step time is over 3 minutes, re-plan before the full runs;
(2) the two 2nd-seed runs go last. Check `prime wallet` after the first three arms, and launch them
only if at least $12 remains (one 2nd seed needs ~$4.50 plus evals).

## 2. Get a node and copy the code

```bash
prime availability list --gpu-type A6000_48GB           # pick a 2-GPU row (~$1.08/hr), note its ID
prime pods create --id <ID> --name honesty-rl --disk-size 200
prime pods list                                         # wait for ACTIVE, note the pod ID
# copy the four project folders (no venvs, no old outputs)
for d in letter-vs-intent caseworker honesty-rl; do
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

## 4. Pilot (~$6): go/no-go

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


## 5. Full runs (~$75)

On the same node, one after another (~20 h), or in parallel on separate nodes (same cost):

```bash
for arm in checklist outcome honest; do bash ~/honesty-rl/scripts/gpu/run_arm.sh $arm; done
prime wallet    # >= $12 left? then the 2nd seed:
for arm in outcome_s2 honest_s2; do bash ~/honesty-rl/scripts/gpu/run_arm.sh $arm; done
```

Each run ends by copying its final LoRA adapter to `~/adapters/<arm>`. Copy all three adapters
to one node for the final evals.

## 6. Final evals (~$18)

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

- Push letter-vs-intent v0.6 and Caseworker v0.2 to the Hub (public).
- Upload the three LoRA adapters to Hugging Face with a model card linking the writeup.
- Publish `docs/WRITEUP_DRAFT.md` (filled in), the configs, and `results/summary.md`.
