#!/usr/bin/env bash
# Final evaluation of the base model and every trained adapter on one node.
#   scripts/gpu/final_evals.sh base checklist outcome honest
# Writes results/<model>/<source>/... for scripts/analyze.py.
set -euo pipefail
MODEL=Qwen/Qwen3.5-4B
OUT=~/honesty-rl/results
unset VLLM_API_KEY   # vLLM would require it as a password; the AB client passes a dummy below
export VLLM_NO_USAGE_STATS=1 VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
cd ~/prime-rl

# One vLLM server with LoRA enabled; adapters are hot-loaded by name.
# Tool/reasoning parsers are left on "auto" (prime-rl maps Qwen3.5 to qwen3_coder / qwen3).
mkdir -p ~/runs
uv run inference --vllm.model "$MODEL" --vllm.enable-lora --vllm.max-lora-rank 16 --vllm.max-model-len 32768 \
  > ~/runs/final_inference.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
until curl -sf localhost:8000/v1/models > /dev/null; do sleep 10; done
curl -s localhost:8000/v1/models | python3 -c "import json,sys; print('served:', [m['id'] for m in json.load(sys.stdin)['data']])"

# The eval judge must be the frozen base model. Use whatever id the server lists for it.
BASE_ID=$(curl -s localhost:8000/v1/models | python3 -c "
import json,sys; ids=[m['id'] for m in json.load(sys.stdin)['data']]
print(next((i for i in ids if i.endswith('-base')), ids[0]))")
mkdir -p /tmp/evalcfg
for f in ~/honesty-rl/configs/eval_src_*.toml; do
  sed "s#model = \"$MODEL-base\"#model = \"$BASE_ID\"#g" "$f" > /tmp/evalcfg/$(basename "$f")
done

for NAME in "$@"; do
  if [ "$NAME" = base ]; then SERVE="$BASE_ID"; else
    SERVE="$NAME"
    BODY="{\"lora_name\": \"$NAME\", \"lora_path\": \"$HOME/adapters/$NAME\"}"
    curl -sf -X POST localhost:8000/v1/load_lora_adapter -H 'Content-Type: application/json' -d "$BODY" \
      || curl -sf -X POST localhost:8000/load_lora_adapter -H 'Content-Type: application/json' -d "$BODY" \
      || { echo "could not load adapter $NAME"; continue; }
    curl -s localhost:8000/v1/models | grep -q "\"$NAME\"" || { echo "adapter $NAME not listed after load"; continue; }
  fi
  echo "=== $NAME (served as $SERVE)"
  # One run per eval source -> results/<model>/<source>/ (sources share task-id formats).
  # 2nd-seed adapters only need the sources the primary tests use.
  # Budget run 2: the sources that carry the hypotheses. SafetyNetBench was 0% for the 4B at step 0 and 40
  # (uninformative); expert/pressure dropped. The honesty-prompt baseline is only needed for the base model.
  SRCS="/tmp/evalcfg/eval_src_potemkin-test-mixed.toml /tmp/evalcfg/eval_src_ifeval.toml"
  [ "$NAME" = base ] && SRCS="$SRCS /tmp/evalcfg/eval_src_potemkin-honesty-prompt.toml"
  for f in $SRCS; do
    SRC=$(basename "$f" .toml); SRC=${SRC#eval_src_}
    uv run eval @ "$f" -m "$SERVE" --run.name "final-$NAME-$SRC" --output-dir ~/runs
    mkdir -p "$OUT/$NAME/$SRC" && cp -r ~/runs/final-$NAME-$SRC/monitors "$OUT/$NAME/$SRC/" 2>/dev/null || true
  done

  # Third-party transfer: Zapier AutomationBench 'simple' domain, with self-reports
  # (the harder domains sit near the floor even for frontier models; skipped to save budget)
  case "$NAME" in *_s2) continue ;; esac
  for D in simple; do
    N=50
    VLLM_API_KEY=EMPTY ~/ab/bin/vf-eval automationbench-honesty -m "$SERVE" -b http://localhost:8000/v1 -k VLLM_API_KEY \
      -n $N -r 2 -c 16 -t 2048 -T 0.7 -a "{\"domains\": \"$D\"}" -s -o "$OUT/$NAME/automationbench-$D"
  done
done
echo "Done. Copy ~/honesty-rl/results back and run: python scripts/analyze.py results --plots"
