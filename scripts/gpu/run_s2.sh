#!/usr/bin/env bash
# Second seed for the outcome and honest arms (40 steps each, they stop themselves), then the
# primary held-out eval for both. Each arm's training metrics + adapter are copied into results/.
#   setsid nohup bash ~/honesty-rl/scripts/gpu/run_s2.sh > ~/runs/run_s2.log 2>&1 &
set -uo pipefail
MODEL=Qwen/Qwen3.5-4B
OUT=~/honesty-rl/results
for arm in outcome_s2 honest_s2; do
  if [ ! -f ~/adapters/$arm/adapter_model.safetensors ]; then
    echo "=== $(date -u +%F' '%T) start $arm"
    timeout 6h bash ~/honesty-rl/scripts/gpu/run_arm.sh $arm || echo "!!! $arm non-zero or hit the 6h cap"
    pkill -f "[p]rime_rl"; pkill -f "[t]orchrun"; sleep 10
  fi
  mkdir -p $OUT/$arm && cp ~/runs/$arm/monitors/file/metrics.jsonl $OUT/$arm/train_metrics.jsonl 2>/dev/null
  cp -r ~/adapters/$arm $OUT/$arm/adapter 2>/dev/null
  sed "s/\x1b\[[0-9;]*m//g" ~/runs/$arm/logs/attempt_1/trainer.log 2>/dev/null | grep "SUCCESS Step" > $OUT/$arm/trainer_steps.log
done
echo "=== $(date -u +%F' '%T) evals"
unset VLLM_API_KEY
export VLLM_NO_USAGE_STATS=1 VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
cd ~/prime-rl
uv run inference --vllm.model "$MODEL" --vllm.enable-lora --vllm.max-lora-rank 16 --vllm.max-model-len 32768 > ~/runs/s2_inference.log 2>&1 &
SERVER=$!
for i in $(seq 1 90); do curl -sf localhost:8000/v1/models > /dev/null && break; sleep 10; done
for NAME in outcome_s2 honest_s2; do
  curl -sf -X POST localhost:8000/v1/load_lora_adapter -H 'Content-Type: application/json' \
    -d "{\"lora_name\": \"$NAME\", \"lora_path\": \"$HOME/adapters/$NAME\"}" || { echo "load failed $NAME"; continue; }
  timeout 2h uv run eval @ ~/honesty-rl/configs/eval_src_potemkin-test-mixed.toml -m "$NAME" --run.name "final-$NAME" --output-dir ~/runs
  mkdir -p $OUT/$NAME/potemkin-test-mixed && cp -r ~/runs/final-$NAME/monitors $OUT/$NAME/potemkin-test-mixed/
done
kill $SERVER 2>/dev/null
echo "=== $(date -u +%F' '%T) S2 DONE"
touch ~/S2_DONE
