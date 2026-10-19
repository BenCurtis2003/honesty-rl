#!/usr/bin/env bash
# IFEval capability check for base + the three trained adapters (closes H4). ~20 min after setup.
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"   # uv, when installed by setup_node.sh
MODEL=Qwen/Qwen3.5-4B
OUT=~/honesty-rl/results
unset VLLM_API_KEY
export VLLM_NO_USAGE_STATS=1 VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
cd ~/prime-rl
mkdir -p ~/runs
uv run inference --vllm.model "$MODEL" --vllm.enable-lora --vllm.max-lora-rank 16 --vllm.max-model-len 32768 > ~/runs/ifeval_inference.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for i in $(seq 1 90); do curl -sf localhost:8000/v1/models > /dev/null && break; sleep 10; done
BASE_ID=$(curl -s localhost:8000/v1/models | python3 -c "import json,sys; ids=[m['id'] for m in json.load(sys.stdin)['data']]; print(next((i for i in ids if i.endswith('-base')), ids[0]))")
echo "base served as $BASE_ID"
for NAME in base checklist outcome honest; do
  if [ "$NAME" = base ]; then SERVE="$BASE_ID"; else
    SERVE="$NAME"
    curl -sf -X POST localhost:8000/v1/load_lora_adapter -H 'Content-Type: application/json' \
      -d "{\"lora_name\": \"$NAME\", \"lora_path\": \"$HOME/adapters/$NAME\"}" || { echo "load failed $NAME"; continue; }
  fi
  timeout 40m uv run eval @ ~/honesty-rl/configs/eval_src_ifeval.toml -m "$SERVE" --run.name "ifeval-$NAME" --output-dir ~/runs
  mkdir -p "$OUT/$NAME/ifeval" && rm -rf "$OUT/$NAME/ifeval/monitors" && cp -r ~/runs/ifeval-$NAME/monitors "$OUT/$NAME/ifeval/"
done
echo "=== IFEVAL DONE"
touch ~/IFEVAL_DONE
