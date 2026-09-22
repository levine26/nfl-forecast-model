# Candidate 3 implementation defect record 002

Status: **mechanical CI/firewall defect after successful frozen evaluation**

Candidate: `ADAPTIVE-MARKET-PATH-INNOVATION-V1`  
Authoritative preregistration SHA: `52cf402cd33da0e535ef963c7d98f9b4304ea208`  
Affected run: `35757718496`

## Failure

The frozen Candidate 3 evaluation completed successfully and all schema/leakage assertions passed. The subsequent production-firewall step failed because the pull-request checkout had `fetch-depth: 1`, so:

`git diff --name-only origin/main...HEAD`

could not locate a merge base.

Observed failure:

`fatal: origin/main...HEAD: no merge base`

This happened after the target result had been calculated. The result was preserved and was not used to alter Candidate 3.

## Correction

Commit `1f17f252f3b93236d5f00eba847871de0ae465d6` changed only the workflow checkout to `fetch-depth: 0`.

No feature, coefficient, threshold, sample, source window, control definition, robustness cell, statistical test, success criterion, or scoring calculation changed.

## Preserved result before repair

Run `35757718496` had already computed:

- F-ST: 179 / 272
- Candidate 3: 180 / 272
- accuracy delta: +0.367647 percentage points
- switches: 3
- Candidate-only correct: 2
- F-ST-only correct: 1
- Candidate Brier: 0.21213037693099118
- F-ST Brier: 0.21157841309047173
- Candidate log loss: 0.6086655020798805
- F-ST log loss: 0.6076199189347058
- frozen-preregistration disposition: **INCONCLUSIVE**

The repaired canonical run `35757935130` reproduced the same result and passed the production firewall.
