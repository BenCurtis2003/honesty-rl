#!/usr/bin/env bash
# After the budget guard pulls seed 2 into results/seed2_run/: build a two-seed results root, write the
# merged tables, and run the preregistered tests on seed 2 alone and on both seeds pooled per task.
#   bash scripts/seed2_wrapup.sh [results_dir]
set -euo pipefail
cd "$(dirname "$0")/.."
R=${1:-results}
S2="$R/seed2_run"
for arm in outcome_s2 honest_s2; do
  [ -d "$S2/$arm/potemkin-test-mixed" ] || { echo "missing $S2/$arm/potemkin-test-mixed"; exit 1; }
done
rm -rf "$R/two_seeds" "$R/seed2_only"; mkdir -p "$R/two_seeds" "$R/seed2_only"
for arm in base checklist outcome honest; do ln -s "../final_evals/$arm" "$R/two_seeds/$arm"; done
for arm in outcome_s2 honest_s2; do ln -s "../seed2_run/$arm" "$R/two_seeds/$arm"; done
for arm in base checklist; do ln -s "../final_evals/$arm" "$R/seed2_only/$arm"; done
ln -s "../seed2_run/outcome_s2" "$R/seed2_only/outcome"; ln -s "../seed2_run/honest_s2" "$R/seed2_only/honest"
PY=.venv/bin/python
$PY scripts/analyze.py "$R/two_seeds" --merge-seeds > "$R/summary_2seeds.md"
{ echo "## Seed 2 alone (outcome and honest arms retrained with seed 23)"; echo
  $PY scripts/hypotheses.py "$R/seed2_only"; echo
  echo "## Both seeds pooled per task (each arm: 2 seeds x 2 attempts per task)"; echo
  $PY scripts/hypotheses.py "$R/two_seeds" --merge-seeds; } | tee "$R/hypotheses_2seeds.md"
echo; echo "wrote $R/summary_2seeds.md and $R/hypotheses_2seeds.md"
