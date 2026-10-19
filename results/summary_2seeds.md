# Results

95% CIs resample tasks (all rollouts of a task move together).


## automationbench-simple

| model | n | Real success | Partial credit | Claimed done | False success | Truthful report |
|---|---|---|---|---|---|---|
| base | 100 | 88% [79-95] | 88% [79-95] | 87% [78-94] | 6% [1-13] | 81% [71-90] |
| checklist | 100 | 87% [78-95] | 87% [78-95] | 89% [82-95] | 12% [5-20] | 77% [67-86] |
| honest | 100 | 89% [81-96] | 89% [81-96] | 89% [81-95] | 8% [3-15] | 81% [72-89] |
| outcome | 100 | 90% [83-96] | 90% [83-96] | 88% [81-94] | 5% [1-10] | 83% [75-90] |

Change vs `base` (paired over shared tasks; p = share of resamples with no improvement):

| model | Real success | Partial credit | Claimed done | False success | Truthful report |
|---|---|---|---|---|---|
| checklist | -1pp [-8, +6] | -1pp [-8, +6] | +2pp [-9, +13] | +6pp [-1, +14] | -4pp [-16, +7] |
| honest | +1pp [-5, +7] | +1pp [-5, +7] | +2pp [-9, +12] | +2pp [-4, +7] | +0pp [-10, +10] |
| outcome | +2pp [-3, +7] | +2pp [-3, +7] | +1pp [-7, +10] | -1pp [-5, +2] | +2pp [-7, +11] |

## potemkin-honesty-prompt

| model | n | Real success | Partial credit | Claimed done | False success | Truthful report | Claims done when done | Checklist grader | Used check tool |
|---|---|---|---|---|---|---|---|---|---|
| base | 168 | 36% [26-45] | 56% [49-64] | 35% [26-45] | 12% [7-19] | 35% [25-44] | 91% [78-100] | 48% [39-57] | 12% [7-18] |

Change vs `base` (paired over shared tasks; p = share of resamples with no improvement):

| model | Real success | Partial credit | Claimed done | False success | Truthful report | Claims done when done | Checklist grader | Used check tool |
|---|---|---|---|---|---|---|---|---|

## potemkin-test-mixed

| model | n | Real success | Partial credit | Claimed done | False success | Truthful report | Claims done when done | Checklist grader | Used check tool |
|---|---|---|---|---|---|---|---|---|---|
| base | 168 | 32% [23-41] | 55% [48-62] | 43% [33-54] | 19% [12-27] | 30% [21-39] | 91% [78-100] | 51% [41-61] | 7% [4-10] |
| checklist | 168 | 32% [23-42] | 55% [47-63] | 49% [39-61] | 18% [10-26] | 32% [22-42] | 97% [90-100] | 55% [45-65] | 14% [8-20] |
| honest | 336 | 46% [36-56] | 61% [53-69] | 32% [23-42] | 5% [2-9] | 45% [36-56] | 95% [86-100] | 50% [42-59] | 5% [3-8] |
| outcome | 336 | 46% [36-56] | 62% [54-70] | 34% [25-44] | 6% [3-10] | 46% [36-56] | 99% [96-100] | 50% [42-59] | 9% [4-14] |

Change vs `base` (paired over shared tasks; p = share of resamples with no improvement):

| model | Real success | Partial credit | Claimed done | False success | Truthful report | Claims done when done | Checklist grader | Used check tool |
|---|---|---|---|---|---|---|---|---|
| checklist | +1pp [-7, +8] | -0pp [-6, +4] | +7pp [+2, +12] | -1pp [-8, +5] | +2pp [-5, +9] | +5pp [+0, +14] | +4pp [+2, +7] | +7pp [+2, +12] |
| honest | +15pp [+8, +22] * | +6pp [+3, +10] * | -11pp [-18, -4] | -14pp [-22, -7] * | +15pp [+9, +23] * | +7pp [+0, +19] | -0pp [-3, +3] | -1pp [-5, +1] |
| outcome | +14pp [+7, +21] * | +7pp [+4, +11] * | -9pp [-16, -1] | -13pp [-21, -7] * | +16pp [+9, +23] * | +7pp [+0, +19] | -0pp [-3, +3] | +2pp [-2, +7] |

`*` = improvement in the good direction with one-sided bootstrap p < 0.05.


## Behavior (means per rollout)

| model | source | turns | tool calls | report words | checked after last write |
|---|---|---|---|---|---|
| base | potemkin-honesty-prompt | 11.0 | 13.7 | 26 | 9% |
| base | potemkin-test-mixed | 10.7 | 13.9 | 26 | 5% |
| checklist | potemkin-test-mixed | 8.6 | 15.7 | 26 | 10% |
| honest | potemkin-test-mixed | 10.9 | 15.2 | 25 | 3% |
| outcome | potemkin-test-mixed | 10.6 | 15.2 | 25 | 6% |
