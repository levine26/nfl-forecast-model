from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
SCRIPT=HERE/"freeze_defensive_efficiency_shadow.py"


def _module():
    spec=importlib.util.spec_from_file_location("freeze_def_eff",SCRIPT)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shadow_fit_horizon_is_pre2026():
    module=_module()
    assert module.TRAINED_THROUGH_SEASON==2025
    assert module.SHADOW_CONTRACT_VERSION=="levline-props-v2-defensive-efficiency-shadow-v0.1.0"


def test_committed_shadow_coefficients_are_locked():
    import json
    frozen=json.loads((HERE/"DEFENSIVE_EFFICIENCY_SHADOW_FROZEN.json").read_text())
    assert frozen["contract_version"]=="levline-props-v2-defensive-efficiency-shadow-v0.1.0"
    assert frozen["trained_through_season"]==2025
    assert frozen["completed_2026_outcomes_used"]==0
    assert frozen["prop_outcomes_used"]==0
    assert frozen["sportsbook_results_used"]==0
    assert frozen["production_authorized"] is False
    assert frozen["fits"]["rushing"]["beta_standardized"]==0.1060375269278496
    assert frozen["fits"]["receiving"]["beta_standardized"]==0.21008097583610338
