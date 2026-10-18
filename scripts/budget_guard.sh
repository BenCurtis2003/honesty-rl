#!/usr/bin/env bash
# Local wallet guard: polls the Prime wallet; if the balance falls below FLOOR, stops all training on
# the pod and terminates it. Also terminates the pod once run_all.sh reports "all done".
#   bash scripts/budget_guard.sh <pod-id> <user@host> <ssh-port> <floor-usd> [--dry-run]
POD=$1; HOST=$2; PORT=$3; FLOOR=$4; DRY=${5:-}
KEY=~/.ssh/prime_personal
SSH="ssh -i $KEY -p $PORT -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=4"
DONE_FILE=${DONE_FILE:-}  # optional: remote file whose existence means "finished"
TO() { perl -e 'alarm shift; exec @ARGV' "$@"; }   # macOS has no `timeout`
export PRIME_DISABLE_VERSION_CHECK=1
while true; do
  BAL=$(TO 60 prime --plain wallet 2>/dev/null | sed -n 's/.*Balance: *\$\([0-9.]*\).*/\1/p' | head -1)
  if [ -n "$DONE_FILE" ]; then
    DONE=$(TO 60 $SSH $HOST "test -f $DONE_FILE && echo 1 || echo 0" 2>/dev/null)
  else
    DONE=$(TO 60 $SSH $HOST 'grep -c "=== .* all done" ~/runs/run_all.log 2>/dev/null' 2>/dev/null)
  fi
  NPODS=$(TO 60 prime --plain pods list 2>/dev/null | grep -c ACTIVE)
  [ "${NPODS:-0}" -gt 1 ] && echo "WARNING: $NPODS active pods (expected 1)"
  echo "$(date -u +%F' '%T) balance=\$$BAL floor=\$$FLOOR done=${DONE:-?}"
  if [ -n "$BAL" ] && awk "BEGIN{exit !($BAL < $FLOOR)}"; then
    echo "BALANCE BELOW FLOOR -> stopping"
    if [ "$DRY" = "--dry-run" ]; then echo "(dry run: would stop training and terminate $POD)"; exit 0; fi
    TO 60 $SSH $HOST 'pkill -f "[r]un_all.sh"; pkill -f "[p]rime_rl"; pkill -f "[t]orchrun"' 2>/dev/null
    echo "NOTE: results stay on the pod disk until terminate; downloading results/ first"
    rsync -az -e "$SSH" $HOST:~/honesty-rl/results/ ~/code/honesty-rl/results/run2_partial/ 2>/dev/null
    prime --plain pods terminate $POD --yes; exit 1
  fi
  if [ "${DONE:-0}" -ge 1 ] 2>/dev/null; then
    echo "run finished -> downloading results, then terminating pod"
    if [ "$DRY" = "--dry-run" ]; then exit 0; fi
    if [ -n "$DONE_FILE" ]; then
      PULL=${PULL_INCLUDE:-ifeval/**}; DEST=${PULL_DEST:-ifeval_run}
      TO 1800 rsync -az -e "$SSH" --include="*/" --include="$PULL" --exclude="*" $HOST:~/honesty-rl/results/ ~/code/honesty-rl/results/$DEST/ \
        && prime --plain pods terminate $POD --yes; exit 0
    fi
    rsync -az -e "$SSH" $HOST:~/honesty-rl/results/ ~/code/honesty-rl/results/ && \
    rsync -az -e "$SSH" --include="*/" --include="metrics.jsonl" --exclude="*" $HOST:~/runs/ ~/code/honesty-rl/results/runs/run2_metrics/ && \
    rsync -az -e "$SSH" $HOST:~/adapters/ ~/code/honesty-rl/results/runs/adapters/ && \
    prime --plain pods terminate $POD --yes; exit 0
  fi
  [ "$DRY" = "--dry-run" ] && exit 0
  sleep 600
done
