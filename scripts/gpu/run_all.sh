#!/usr/bin/env bash
# Run 2: outcome and honest arms (40 steps each, they stop themselves), then the final evals.
# Each stage has a wall-clock cap so nothing can run away.
#   setsid nohup bash ~/honesty-rl/scripts/gpu/run_all.sh > ~/runs/run_all.log 2>&1 &
set -uo pipefail
for arm in outcome honest; do
  if [ -f ~/adapters/$arm/adapter_model.safetensors ]; then echo "skip $arm (adapter exists)"; continue; fi
  echo "=== $(date -u +%F' '%T) start $arm"
  timeout 7h bash ~/honesty-rl/scripts/gpu/run_arm.sh $arm || echo "!!! $arm exited non-zero or hit the 7h cap"
  pkill -f "[p]rime_rl"; pkill -f "[t]orchrun"; sleep 10
done
echo "=== $(date -u +%F' '%T) final evals"
timeout 5h bash ~/honesty-rl/scripts/gpu/final_evals.sh base outcome honest checklist || echo "!!! final evals non-zero or hit the 5h cap"
echo "=== $(date -u +%F' '%T) all done"
