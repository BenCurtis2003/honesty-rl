#!/usr/bin/env bash
# Stop a running arm cleanly at a given step, keeping that step's LoRA adapter.
#   setsid nohup bash stop_at_step.sh checklist 70 > ~/runs/stop_checklist.log 2>&1 &
ARM=$1; STEP=$2
LOG=~/runs/$ARM/logs/attempt_1/trainer.log
until grep -q "SUCCESS Step $STEP |" "$LOG" 2>/dev/null; do sleep 20; done
until [ -f ~/runs/$ARM/broadcasts/step_$STEP/adapter_model.safetensors ]; do sleep 5; done
sleep 10
mkdir -p ~/adapters && rm -rf ~/adapters/$ARM && cp -r ~/runs/$ARM/broadcasts/step_$STEP ~/adapters/$ARM
echo "$(date -u +%T) saved step_$STEP adapter -> ~/adapters/$ARM"
pkill -f "[p]rime_rl"; pkill -f "[t]orchrun"
for p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader); do kill $p; done
echo "$(date -u +%T) stopped $ARM at step $STEP"
