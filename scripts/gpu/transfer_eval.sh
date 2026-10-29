#!/usr/bin/env bash
# Transfer test: does the adapter trained on one AP workflow (results/workflow_full) change behavior on the
# held-out PotemkinBench test set (84 mixed tasks from other templates) and on IFEval?
# Compare with results/final_evals/base (same eval configs). Touches ~/TR_DONE when finished.
#   setsid nohup bash ~/honesty-rl/scripts/gpu/transfer_eval.sh > ~/runs/transfer.log 2>&1 &
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"
MODEL=Qwen/Qwen3.5-4B
OUT=~/honesty-rl/results/transfer
unset VLLM_API_KEY
export VLLM_NO_USAGE_STATS=1 VLLM_ALLOW_RUNTIME_LORA_UPDATING=True WANDB_MODE=offline
cd ~/prime-rl; mkdir -p ~/runs $OUT /tmp/evalcfg
uv run inference --vllm.model "$MODEL" --vllm.enable-lora --vllm.max-lora-rank 16 --vllm.max-model-len 32768 \
  > ~/runs/transfer_inference.log 2>&1 &
SERVER=$!
for i in $(seq 1 90); do curl -sf localhost:8000/v1/models > /dev/null && break; sleep 10; done
BASE_ID=$(curl -s localhost:8000/v1/models | python3 -c "
import json,sys; ids=[m['id'] for m in json.load(sys.stdin)['data']]
print(next((i for i in ids if i.endswith('-base')), ids[0]))")
for f in ~/honesty-rl/configs/eval_src_potemkin-test-mixed.toml ~/honesty-rl/configs/eval_src_ifeval.toml; do
  sed "s#model = \"$MODEL-base\"#model = \"$BASE_ID\"#g" "$f" > /tmp/evalcfg/$(basename "$f")
done
curl -sf -X POST localhost:8000/v1/load_lora_adapter -H 'Content-Type: application/json' \
  -d "{\"lora_name\": \"ap_workflow\", \"lora_path\": \"$HOME/adapters/ap_workflow\"}" || { echo "lora load failed"; touch ~/TR_DONE; exit 1; }
for SRC in ${SRCS:-potemkin-test-mixed}; do
  echo "=== $(date -u +%T) ap_workflow on $SRC"
  timeout 2h uv run eval @ /tmp/evalcfg/eval_src_$SRC.toml -m ap_workflow --run.name "transfer-$SRC" --output-dir ~/runs
  mkdir -p $OUT/ap_workflow/$SRC && cp -r ~/runs/transfer-$SRC/monitors $OUT/ap_workflow/$SRC/ 2>/dev/null
done
kill $SERVER 2>/dev/null
echo "=== $(date -u +%T) DONE"; echo DONE > $OUT/STATUS; touch ~/TR_DONE
