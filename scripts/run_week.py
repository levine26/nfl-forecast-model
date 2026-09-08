from __future__ import annotations

import argparse
from nfl_forecast.pipeline import run, write_outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--snapshot", choices=["EARLY","FINAL"], default="EARLY")
    parser.add_argument("--config", default="config/model.yaml")
    args = parser.parse_args()
    artifacts = run(args.config, args.season, args.snapshot)
    write_outputs(artifacts, "outputs")
    print(artifacts.predictions[["away_team","home_team","final_home_prob","pick","expected_margin","expected_total","confidence"]].to_string(index=False))


if __name__ == "__main__":
    main()
