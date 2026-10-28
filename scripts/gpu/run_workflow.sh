#!/usr/bin/env bash
# GPUS=1 runs inference and trainer on one GPU (rl_workflow_1gpu.toml + share-gpu patch); SMOKE=1 trains 2 steps only.
# Workflow run: train Qwen3.5-4B on one customer-style workflow (workflows/ap_payment_lite.yaml) and compare
# base vs trained on 40 held-out instances. Stops early (no training) if the base model's success is outside
# the learnable range. Touches ~/WF_DONE when finished, so budget_guard.sh (DONE_FILE) pulls results and stops
# the pod.
#   setsid nohup bash ~/honesty-rl/scripts/gpu/run_workflow.sh > ~/runs/run_workflow.log 2>&1 &
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"
MODEL=Qwen/Qwen3.5-4B
WF=${WF:-$HOME/honesty-rl/workflows/ap_payment_lite.yaml}
OUT=~/honesty-rl/results/workflow_run
mkdir -p ~/runs /tmp/wfcfg $OUT
RLCFG=rl_workflow; [ "${GPUS:-2}" = 1 ] && RLCFG=rl_workflow_1gpu && export PRL_SHARE_GPU=1
for c in $RLCFG eval_src_workflow; do sed "s#__WF__#$WF#" ~/honesty-rl/configs/$c.toml > /tmp/wfcfg/$c.toml; done
unset VLLM_API_KEY
export VLLM_NO_USAGE_STATS=1 VLLM_ALLOW_RUNTIME_LORA_UPDATING=True WANDB_MODE=${WANDB_MODE:-offline}
cd ~/prime-rl

serve() {  # $1 = extra vllm args
  uv run inference --vllm.model "$MODEL" $1 --vllm.max-model-len 32768 > ~/runs/wf_inference.log 2>&1 &
  SERVER=$!
  for i in $(seq 1 90); do curl -sf localhost:8000/v1/models > /dev/null && return 0; sleep 10; done
  echo "!!! inference server did not start"; return 1
}
evaluate() {  # $1 = model or lora name, $2 = results name
  timeout 2h uv run eval @ /tmp/wfcfg/eval_src_workflow.toml -m "$1" --run.name "wf-$2" --output-dir ~/runs
  mkdir -p $OUT/$2/ap-workflow-test && cp -r ~/runs/wf-$2/monitors $OUT/$2/ap-workflow-test/
}
finish() { echo "=== $(date -u +%F' '%T) $1"; echo "$1" > $OUT/STATUS; touch ~/WF_DONE; exit 0; }

echo "=== $(date -u +%F' '%T) base eval"
serve "" || finish "FAILED: server (base)"
evaluate "$MODEL" base
kill $SERVER 2>/dev/null; sleep 15; pkill -f "[v]llm" ; sleep 5

BASE=$(cd ~/honesty-rl && ~/prime-rl/.venv/bin/python - <<'PY'
import pathlib, sys
sys.path.insert(0, "scripts")
from analyze import load, mean
rows = load(pathlib.Path("results/workflow_run")).get("base", {}).get("ap-workflow-test", [])
print(f"{mean([r['success'] for r in rows]):.3f} {len(rows)}")
PY
)
echo "base success, rollouts: $BASE"
read S N <<< "$BASE"
if [ "${N:-0}" -lt 20 ] || awk "BEGIN{exit !($S < 0.05 || $S > 0.90)}"; then
  finish "STOPPED before training: base success $S on $N rollouts is outside 0.05-0.90"
fi

echo "=== $(date -u +%F' '%T) train"
EXTRA=""; [ "${SMOKE:-0}" = 1 ] && EXTRA="--max-steps 2"
timeout ${TRAIN_TIMEOUT:-6h} uv run rl @ /tmp/wfcfg/$RLCFG.toml --run.name workflow --output-dir ~/runs $EXTRA 2>&1 | tee ~/runs/workflow.log \
  || echo "!!! training non-zero or hit the 6h cap"
pkill -f "[p]rime_rl"; pkill -f "[t]orchrun"; sleep 10
LAST=$(ls -d ~/runs/workflow/broadcasts/step_* 2>/dev/null | sort -V | tail -1)
[ -n "$LAST" ] || finish "FAILED: no adapter saved"
mkdir -p ~/adapters && rm -rf ~/adapters/workflow && cp -r "$LAST" ~/adapters/workflow
cp ~/runs/workflow/monitors/file/metrics.jsonl $OUT/train_metrics.jsonl 2>/dev/null
cp -r ~/adapters/workflow $OUT/adapter 2>/dev/null
echo "adapter from $LAST"

echo "=== $(date -u +%F' '%T) trained eval"
serve "--vllm.enable-lora --vllm.max-lora-rank 16" || finish "FAILED: server (trained)"
curl -sf -X POST localhost:8000/v1/load_lora_adapter -H 'Content-Type: application/json' \
  -d "{\"lora_name\": \"workflow\", \"lora_path\": \"$HOME/adapters/workflow\"}" || finish "FAILED: lora load"
evaluate workflow trained
kill $SERVER 2>/dev/null
finish "DONE"
