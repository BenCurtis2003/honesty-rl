#!/usr/bin/env bash
# ~$2 pilot: 20 steps of the checklist arm + online evals at steps 0/10/20. Go/no-go is in docs/RUNBOOK.md.
set -euo pipefail
cd ~/prime-rl
unset VLLM_API_KEY   # if set, vLLM demands it as a password and the orchestrator gets 401
export VLLM_NO_USAGE_STATS=1 WANDB_MODE=${WANDB_MODE:-offline}
mkdir -p ~/runs
uv run rl @ ~/honesty-rl/configs/pilot.toml --run.name pilot --output-dir ~/runs 2>&1 | tee ~/runs/pilot.log
