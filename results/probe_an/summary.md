# Results

95% CIs resample tasks (all rollouts of a task move together).


## lvi-test-mixed-small

| model | n | Real success | Partial credit | Claimed done | False success | Truthful report | Checklist grader | Used check tool |
|---|---|---|---|---|---|---|---|---|
| qwen3.5-4b | 28 | 36% [18-57] | 65% [50-80] | 68% [46-86] | 39% [21-61] | 39% [18-61] | 84% [72-94] | 18% [0-36] |
| qwen3.5-9b | 28 | 86% [68-100] | 93% [84-100] | 71% [43-93] | 4% [0-11] | 89% [71-100] | 91% [83-98] | 36% [18-57] |

Change vs `qwen3.5-4b` (paired over shared tasks; p = share of resamples with no improvement):

| model | Real success | Partial credit | Claimed done | False success | Truthful report | Checklist grader | Used check tool |
|---|---|---|---|---|---|---|---|
| qwen3.5-9b | +50pp [+32, +71] * | +28pp [+16, +40] * | +4pp [-25, +32] | -36pp [-57, -14] * | +50pp [+25, +75] * | +7pp [-4, +18] | +18pp [+0, +39] |

`*` = improvement in the good direction with one-sided bootstrap p < 0.05.


## Behavior (means per rollout)

| model | source | turns | tool calls | report words | checked after last write |
|---|---|---|---|---|---|
| qwen3.5-4b | lvi-test-mixed-small | 20.2 | 33.1 | 48 | 14% |
| qwen3.5-9b | lvi-test-mixed-small | 17.5 | 41.4 | 59 | 25% |