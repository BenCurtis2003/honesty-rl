#!/usr/bin/env bash
# Train one arm: scripts/gpu/run_arm.sh checklist|outcome|honest
# One node runs one arm (~4-8 h). For all three in parallel, rent three nodes.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"   # uv, when installed by setup_node.sh
ARM=${1:?usage: run_arm.sh checklist|outcome|honest|outcome_s2|honest_s2}
cd ~/prime-rl
unset VLLM_API_KEY   # if set, vLLM demands it as a password and the orchestrator gets 401
export VLLM_NO_USAGE_STATS=1 WANDB_MODE=${WANDB_MODE:-offline}
mkdir -p ~/runs
uv run rl @ ~/honesty-rl/configs/rl_${ARM}.toml --run.name "$ARM" --output-dir ~/runs 2>&1 | tee ~/runs/${ARM}.log
# Final LoRA adapter for evals + release: newest broadcast dir holds adapter_model.safetensors + adapter_config.json
if [ -f ~/adapters/${ARM}/adapter_model.safetensors ]; then echo "adapter already saved for ${ARM}"; exit 0; fi
LAST=$(ls -d ~/runs/${ARM}/broadcasts/step_* 2>/dev/null | sort -V | tail -1)
mkdir -p ~/adapters && cp -r "$LAST" ~/adapters/${ARM} && echo "adapter -> ~/adapters/${ARM} (from $LAST)"
