#!/usr/bin/env bash
# One-time setup on a fresh 2-GPU node (2x A6000 48GB used here). Run from the node's home directory
# after copying the four project folders there (see docs/RUNBOOK.md, step 2).
set -euo pipefail
PRIME_RL_COMMIT=0956a8858005019b7b16d26898142063ec1bb5e8   # validated configs against this commit
cd ~
# some provider images ship without uv
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh || true; }   # installer can fail on shell-profile edits after installing
export PATH="$HOME/.local/bin:$PATH"
git config --global url."https://github.com/".insteadOf "git@github.com:"   # submodules use SSH URLs
[ -d prime-rl ] || git clone https://github.com/PrimeIntellect-ai/prime-rl.git
cd prime-rl && git checkout -q "$PRIME_RL_COMMIT" \
  && (git apply --check ~/honesty-rl/patches/prime-rl-qwen3_5-tied-lm-head.patch 2>/dev/null && git apply ~/honesty-rl/patches/prime-rl-qwen3_5-tied-lm-head.patch || echo "tied lm_head patch already applied") && git submodule update --init --recursive \
  && git submodule foreach --recursive "git checkout -f -q HEAD" && uv sync --all-extras   # empty-tree submodules; GPU extras (torch, vllm, flash-attn)

# Our environments + the capability-check env, into prime-rl's venv
uv pip install -e ~/potemkin-bench/environments/potemkin_bench -e ~/safety-net-bench/environments/safety_net_bench
# prime-rl pins an upload-date cutoff, which filters out Hub wheels that carry no upload date
uv pip install --no-config --python .venv/bin/python ifeval --extra-index-url https://hub.primeintellect.ai/primeintellect/ifeval/install/simple/
# IFEval declares "no network", which the subprocess runtime can't enforce; it is single-turn with no
# tools, so allow network to let it run under subprocess (otherwise every task errors).
IFP=$(uv run python -c "import ifeval.taskset as t; print(t.__file__)")
sed -i 's/^    network_allow: list\[str\] = \[\]$/    network_allow: list[str] = ["*"]  # honesty-rl patch/' "$IFP" && grep -n network_allow "$IFP"
uv run python -c "import potemkin_bench, safety_net_bench, ifeval; print('envs import ok')"

# AutomationBench (older verifiers API) gets its own venv; eval-only
uv venv -q --python 3.12 ~/ab
uv pip install --no-config --python ~/ab/bin/python "verifiers==0.3.1" automationbench \
  --extra-index-url https://hub.primeintellect.ai/zapier/AutomationBench/install/simple/
uv pip install --no-config --python ~/ab/bin/python -e ~/honesty-rl/envs/automationbench_honesty

# Offline checks before any GPU time is spent
cd ~/potemkin-bench && for t in tests/test_*.py; do ~/prime-rl/.venv/bin/python "$t"; done
cd ~/safety-net-bench && ~/prime-rl/.venv/bin/python -m pytest -q tests
cd ~/honesty-rl && ~/prime-rl/.venv/bin/python scripts/validate_configs.py

echo "Setup done. Next: wandb login, then scripts/gpu/pilot.sh"
