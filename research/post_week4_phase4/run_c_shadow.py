"""Offline frozen Candidate C snapshot scorer; writes once, no live network or labels."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from research.post_week4_phase4.c_shadow import score_snapshot,write_once


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--frozen-model",required=True)
    parser.add_argument("--pregame-snapshot",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    model=json.loads(Path(args.frozen_model).read_text())
    snapshot=json.loads(Path(args.pregame_snapshot).read_text())
    record=score_snapshot(snapshot,model)
    digest=write_once(Path(args.output),record)
    print(json.dumps({"game_id":record["game_id"],"prediction_sha256":digest,
                      "candidate_home_prob":record["candidate_home_prob"],
                      "status":"FROZEN_RESEARCH_SHADOW",
                      "production_changed":False}))


if __name__=="__main__":
    main()
