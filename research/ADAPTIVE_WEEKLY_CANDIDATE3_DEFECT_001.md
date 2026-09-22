# Candidate 3 implementation defect record 001

Status: **mechanical CI/import defect; no Candidate 3 target result was produced**

Candidate: `ADAPTIVE-MARKET-PATH-INNOVATION-V1`  
Frozen preregistration SHA: `52cf402cd33da0e535ef963c7d98f9b4304ea208`  
Failed workflow run: `35757581462`  
Failed execution SHA: `3cb3c84c71dfb281cc4e4213e5a38daefd0a4241`

## Failure

The frozen evaluation command failed on Python import before loading the F-ST target vector, before constructing Candidate 3 probabilities, and before scoring any target outcome:

`ModuleNotFoundError: No module named 'nfl_forecast'`

The repository uses a `src/` layout. The workflow invoked the script with `PYTHONPATH=.`, which did not expose `src/nfl_forecast`.

## Correction

Commit `13f013b363a87343914fb8352aa30b29941223a2` changes only the workflow invocation from:

`PYTHONPATH=. ...`

to:

`PYTHONPATH=src:. ...`

No Candidate 3 code, feature definition, coefficient, threshold, source window, sample, control, robustness grid, success band, or statistical test changed.

## Scientific interpretation

Because the failed process terminated at module import, it produced no Candidate 3 target result capable of informing a performance-driven correction. The candidate identity remains `ADAPTIVE-MARKET-PATH-INNOVATION-V1`; this is an execution-environment repair rather than a model revision.

The failed run remains preserved as part of the research record.
