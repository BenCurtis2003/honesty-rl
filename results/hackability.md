## Reward hackability audit (mean reward; scripted policies, no model)

### potemkin-bench, mixed level, small scale (70 tasks)

| policy | strict | partial | honest | honest_partial | checklist | letter |
|---|---|---|---|---|---|---|
| full_honest | 1.00 | 1.00 | 1.00 | 1.00 | 0.93 | 0.76 |
| full_underclaim | 0.96 | 0.99 | 0.80 | 0.78 | 0.70 | 0.00 |
| full_silent | 0.71 | 0.92 | 0.54 | 0.64 | 0.70 | 0.00 |
| half_admit | 0.14 | 0.41 | 0.56 | 0.58 | 0.38 | 0.00 |
| half_claim | 0.00 | 0.33 | 0.00 | 0.23 | 0.68 | 1.00 |
| junk_claim | 0.00 | 0.45 | 0.00 | 0.32 | 1.00 | 1.00 |
| claim_only | 0.00 | 0.27 | 0.00 | 0.19 | 0.35 | 1.00 |

Does cheating pay? (yes = the cheating policy outscores honest half-work)

| test | strict | partial | honest | honest_partial | checklist | letter |
|---|---|---|---|---|---|---|
| lying about the same work (half_claim) | no | no | no | no | **yes** | **yes** |
| lying with no work (claim_only) | no | no | no | no | no | **yes** |
| junk work + lying (junk_claim) | no | **yes** | no | no | **yes** | **yes** |

### SafetyNetBench, 5-case batches (35 batches)

| policy | strict | partial | honest | honest_partial | checklist | letter |
|---|---|---|---|---|---|---|
| full_honest | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| full_underclaim | 1.00 | 1.00 | 0.75 | 0.70 | 0.70 | 0.00 |
| full_silent | 1.00 | 1.00 | 0.75 | 0.70 | 0.70 | 0.00 |
| half_admit | 0.00 | 0.40 | 0.50 | 0.58 | 0.37 | 0.00 |
| half_claim | 0.00 | 0.40 | 0.00 | 0.28 | 0.67 | 1.00 |
| junk_claim | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 |
| claim_only | 0.00 | 0.00 | 0.00 | 0.00 | 0.30 | 1.00 |

Does cheating pay? (yes = the cheating policy outscores honest half-work)

| test | strict | partial | honest | honest_partial | checklist | letter |
|---|---|---|---|---|---|---|
| lying about the same work (half_claim) | no | no | no | no | **yes** | **yes** |
| lying with no work (claim_only) | no | no | no | no | no | **yes** |
| junk work + lying (junk_claim) | no | no | no | no | **yes** | **yes** |
