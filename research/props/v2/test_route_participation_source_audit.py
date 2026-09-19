from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/"research"/"props"/"v2"/"audit_route_participation_source.py"


def _module():
    spec=importlib.util.spec_from_file_location("route_source_audit_tested",SCRIPT)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m


def test_schema_audit_does_not_relabel_on_field_participation_as_route():
    m=_module()
    frame=pd.DataFrame([
        {
            "nflverse_game_id":"g","play_id":1,
            "offense_players":"a;b;c","offense_personnel":"11",
            "number_of_pass_rushers":4,
        }
    ])
    audit=m.summarize(frame,2024)
    assert audit["rows"]==1
    assert audit["unique_plays"]==1
    assert "offense_players" in audit["field_groups"]["offense_players"]
    assert audit["field_groups"]["route_like"]==[]


def test_route_named_fields_are_only_inventory_not_semantic_claim():
    m=_module()
    frame=pd.DataFrame([{"game_id":"g","play_id":1,"route_guess":"x"}])
    audit=m.summarize(frame,2022)
    assert audit["field_groups"]["route_like"]==["route_guess"]
