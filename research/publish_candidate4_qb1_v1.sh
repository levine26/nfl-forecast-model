#!/usr/bin/env bash
# Research-only publication. No pregame data is regenerated on a push retry.
set -euo pipefail

cd "${GITHUB_WORKSPACE:-$PWD}"
DATA_DIR=research_outputs/adaptive_candidate4
if [ ! -s "$DATA_DIR/qb1_t120_snapshots.csv" ]; then
  echo 'No Candidate 4 T-120 QB1 snapshot rows are ready.'
  exit 0
fi

: "${RUNNER_TEMP:?RUNNER_TEMP must be an isolated runner directory}"
PENDING="$RUNNER_TEMP/candidate4-qb1-pending.csv"
WORKTREE="$RUNNER_TEMP/candidate4-qb1-publish"
DATA_BRANCH=research-data/inactive-snapshots-v1

# Exact captured bytes, even after another worker changes the shared branch.
cp "$DATA_DIR/qb1_t120_snapshots.csv" "$PENDING"
git fetch origin "refs/heads/${DATA_BRANCH}:refs/remotes/origin/${DATA_BRANCH}"
# Never checkout over the restored/untracked raw source research_outputs tree.
git worktree add --detach "$WORKTREE" "refs/remotes/origin/${DATA_BRANCH}"
trap 'git worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true' EXIT
git -C "$WORKTREE" config user.name 'levline-research-bot'
git -C "$WORKTREE" config user.email 'actions@users.noreply.github.com'

for attempt in 1 2 3; do
  if [ "$attempt" -gt 1 ]; then
    git -C "$WORKTREE" reset --hard "refs/remotes/origin/${DATA_BRANCH}"
  fi
  DEST="$WORKTREE/research_outputs/adaptive_candidate4/qb1_t120_snapshots.csv"
  # Only the QB1 CSV is reconciled; preserve other remote research files.
  PYTHONPATH="$GITHUB_WORKSPACE/src:$GITHUB_WORKSPACE" \
    python - "$DEST" "$PENDING" <<'PY'
from pathlib import Path
import json
import sys
from research.qb1_t120_ledger_publish_v1 import reconcile_qb1_ledger
print(json.dumps(reconcile_qb1_ledger(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))
PY

  git -C "$WORKTREE" add -- research_outputs/adaptive_candidate4/qb1_t120_snapshots.csv
  if git -C "$WORKTREE" diff --cached --quiet; then
    echo 'Candidate 4 QB1 ledger already present, no rewrite.'
    exit 0
  fi

  git -C "$WORKTREE" commit -m 'Append original Candidate 4 T-120 QB1 capture'
  base_sha=$(git -C "$WORKTREE" rev-parse HEAD^)
  if git -C "$WORKTREE" push origin "HEAD:refs/heads/${DATA_BRANCH}"; then
    echo 'Candidate 4 QB1 ledger published to research-data branch.'
    exit 0
  fi

  git -C "$WORKTREE" fetch origin "refs/heads/${DATA_BRANCH}:refs/remotes/origin/${DATA_BRANCH}"
  if [ "$(git -C "$WORKTREE" rev-parse "refs/remotes/origin/${DATA_BRANCH}")" = "$base_sha" ]; then
    echo 'Push failed without branch advancement; refusing to mask remote failure.' >&2
    exit 1
  fi
  echo "Research-data branch advanced; recheck unchanged captured bytes (attempt $attempt/3)."
done

echo 'QB1 capture could not be durably published after bounded retries.' >&2
exit 1
