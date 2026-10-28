"""Validate every config against prime-rl's own schema (no GPU, no model calls).

  .venv-cfg/bin/python scripts/validate_configs.py
"""

import glob
import sys
import tomllib

from prime_rl.configs.eval import EvalConfig
from prime_rl.configs.rl import RLConfig


def main() -> int:
    bad = 0
    for path in sorted(glob.glob("configs/*.toml")):
        if "hosted_template" in path:
            continue
        data = tomllib.load(open(path, "rb"))
        cls = EvalConfig if "eval_" in path else RLConfig
        try:
            cfg = cls.model_validate(data)
            extra = ""
            if cls is RLConfig:
                src = cfg.orchestrator.train.source[0]
                task = src.env.taskset.task
                evals = [s.resolved_name for s in cfg.orchestrator.eval.source] if cfg.orchestrator.eval else []
                extra = f"reward_mode={task.reward_mode} evals={evals}"
            print(f"OK   {path} {extra}")
        except Exception as e:  # noqa: BLE001
            bad += 1
            print(f"FAIL {path}\n{str(e)[:2500]}\n")
    return bad


if __name__ == "__main__":
    sys.exit(main())
