"""Run the *real* QB1 publication shell against an isolated local Git remote.

These fixtures test Git checkout/push semantics, not live timestamp provenance.
No code can write to the actual research-data branch during this test.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
import shutil
import subprocess

import pytest


SCRIPT = Path(__file__).with_name("publish_candidate4_qb1_v1.sh")
HELPER = Path(__file__).with_name("qb1_t120_ledger_publish_v1.py")
REF = "refs/heads/research-data/inactive-snapshots-v1"
CSV_PATH = "research_outputs/adaptive_candidate4/qb1_t120_snapshots.csv"
COLUMNS = [
    "game_id", "qb1_snapshot_sha256", "candidate_id", "captured_at_utc",
    "t120_target_utc", "kickoff_utc", "research_only",
    "production_authorized", "completed_2026_outcomes_used",
    "home_t120_qb1_player_name",
]


def cmd(*argv, cwd=None, env=None, ok=True):
    p = subprocess.run(argv, cwd=cwd, env=env, text=True,
                       capture_output=True, check=False)
    if ok and p.returncode:
        raise AssertionError(f"{argv!r} failed: {p.stdout}\n{p.stderr}")
    return p


def row(game, digest):
    return {
        "game_id": game, "qb1_snapshot_sha256": digest,
        "candidate_id": "ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1",
        "captured_at_utc": "2026-10-11T18:55:00Z",
        "t120_target_utc": "2026-10-11T19:00:00Z",
        "kickoff_utc": "2026-10-11T21:00:00Z",
        "research_only": "True",
        "production_authorized": "False",
        "completed_2026_outcomes_used": "0",
        "home_t120_qb1_player_name": "QB One",
    }


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def setup_fake_repo(tmp_path, *, with_branch=True):
    remote = tmp_path / "upstream.git"
    source = tmp_path / "source"
    cmd("git", "init", "--bare", str(remote))
    cmd("git", "clone", str(remote), str(source))
    cmd("git", "config", "user.name", "Research CI", cwd=source)
    cmd("git", "config", "user.email", "research@example.invalid", cwd=source)
    (source / "research").mkdir()
    shutil.copyfile(SCRIPT, source / "research" / SCRIPT.name)
    shutil.copyfile(HELPER, source / "research" / HELPER.name)
    (source / "README.md").write_text("Isolated test repository\n")
    cmd("git", "add", ".", cwd=source)
    cmd("git", "commit", "-m", "Seed test main", cwd=source)
    cmd("git", "branch", "-M", "main", cwd=source)
    cmd("git", "push", "-u", "origin", "main", cwd=source)
    cmd("git", "symbolic-ref", "HEAD", "refs/heads/main", cwd=remote)
    if with_branch:
        cmd("git", "checkout", "-b", "research-data/inactive-snapshots-v1", cwd=source)
        write_rows(source / CSV_PATH, [row("2026_04_OLD_GAME", "a" * 64)])
        extra = source / "research_outputs" / "adaptive_candidate4" / "qb_state.csv"
        extra.write_bytes(b"other immutable research state\n")
        cmd("git", "add", "research_outputs", cwd=source)
        cmd("git", "commit", "-m", "Seed original research data", cwd=source)
        cmd("git", "push", "origin", REF, cwd=source)
        cmd("git", "checkout", "main", cwd=source)
    return remote, source


def run_real_script(source, tmp_path, *, success=True):
    env = {**os.environ, "GITHUB_WORKSPACE": str(source),
           "RUNNER_TEMP": str(tmp_path / "scratch")}
    Path(env["RUNNER_TEMP"]).mkdir(exist_ok=True)
    p = cmd("bash", str(source / "research" / SCRIPT.name),
            cwd=source, env=env, ok=False)
    if success:
        assert p.returncode == 0, p.stdout + "\n" + p.stderr
    else:
        assert p.returncode != 0, p.stdout + "\n" + p.stderr
    return p


def remote_bytes(remote, path=CSV_PATH):
    return cmd("git", "--git-dir", str(remote), "show", f"{REF}:{path}").stdout.encode()


def remote_head(remote):
    return cmd("git", "--git-dir", str(remote), "rev-parse", REF).stdout.strip()


def test_worktree_publish_with_restored_untracked_file_and_repeat(tmp_path):
    remote, source = setup_fake_repo(tmp_path)
    # The original checkout -B failed specifically because this file was
    # untracked in main and tracked in the destination branch.
    incoming = source / CSV_PATH
    write_rows(incoming, [row("2026_04_OLD_GAME", "a"*64),
                          row("2026_05_NEW_GAME", "b"*64)])
    before = incoming.read_bytes()
    assert not cmd("git", "ls-files", "--error-unmatch", CSV_PATH,
                   cwd=source, ok=False).returncode == 0

    run_real_script(source, tmp_path)
    assert incoming.read_bytes() == before
    published = remote_bytes(remote).decode()
    assert "2026_05_NEW_GAME" in published
    assert "2026_04_OLD_GAME" in published
    assert remote_bytes(remote, "research_outputs/adaptive_candidate4/qb_state.csv") == (
        b"other immutable research state\n")
    first_head = remote_head(remote)

    again = run_real_script(source, tmp_path)
    assert "already present" in again.stdout
    assert remote_head(remote) == first_head
    assert incoming.read_bytes() == before


def test_conflicting_immutable_snapshot_never_changes_remote(tmp_path):
    remote, source = setup_fake_repo(tmp_path)
    before_head, before = remote_head(remote), remote_bytes(remote)
    write_rows(source / CSV_PATH, [row("2026_04_OLD_GAME", "c"*64)])
    result = run_real_script(source, tmp_path, success=False)
    assert "Immutable QB1 T-120 conflict" in result.stderr
    assert remote_head(remote) == before_head
    assert remote_bytes(remote) == before


def test_missing_source_is_noop_and_keeps_data_remote(tmp_path):
    remote, source = setup_fake_repo(tmp_path)
    before = remote_head(remote)
    result = run_real_script(source, tmp_path)
    assert "No Candidate 4 T-120 QB1 snapshot" in result.stdout
    assert remote_head(remote) == before


def test_missing_remote_data_branch_fails_closed(tmp_path):
    remote, source = setup_fake_repo(tmp_path, with_branch=False)
    write_rows(source / CSV_PATH, [row("2026_05_NEW_GAME", "b"*64)])
    run_real_script(source, tmp_path, success=False)
    assert cmd("git", "--git-dir", str(remote), "rev-parse", "--verify",
               REF, ok=False).returncode != 0
