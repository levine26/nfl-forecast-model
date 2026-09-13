from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

MODULE_PATH = Path(__file__).with_name('v09b_modern_dnp_contradiction_kickoff_chronology_v1.py')
spec = importlib.util.spec_from_file_location('v09b_chronology_under_test', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


def test_contract_shape_and_authority(tmp_path: Path):
    contract = json.loads(Path('research/availability/v09b_modern_dnp_contradiction_kickoff_chronology_v1_contract.json').read_text())
    assert contract['contract_id'] == module.CONTRACT_ID
    assert contract['status'] == 'PREREGISTERED_DIAGNOSTIC_ONLY_NO_MEMBERSHIP_OR_MODEL_AUTHORITY'
    partitions = contract['frozen_scope']['partitions']
    assert len(partitions) == 7
    assert sum(len(p['dnp_rows']) for p in partitions) == 17
    assert sum(bool(p['active_max_contradiction']) for p in partitions) == 6
    assert sum(bool(p['total_roster_max_contradiction']) for p in partitions) == 3
    assert sum(int(p['minimum_dnp_non_active_required_by_active_max']) for p in partitions) == 7
    assert contract['authority']['modern_player_team_game_identity_qualified'] is True
    assert contract['authority']['modern_game_day_roster_universe_qualified'] is False
    assert contract['authority']['training_label_semantics_qualified'] is False
    assert contract['authority']['training_source_chronology_qualified'] is False
    assert contract['authority']['v09b_model_fit_authorized'] is False
    assert contract['governance']['completed_2026_outcomes_used'] == 0


def test_transaction_clause_is_player_local():
    assert module.classify(
        'transaction_article',
        'Placed CB <<<PLAYER>>> on Reserve/Injured; waived DE Damontre Moore.',
        'Placed CB Daryl Worley on Reserve/Injured; waived DE Damontre Moore.',
    ) == ('RESERVE_IR', 'NOT_APPLICABLE_NOT_ROSTER_ELIGIBLE')
    assert module.classify(
        'transaction_article',
        "Placed CB Daryl Worley on Reserve/Injured; waived DE <<<PLAYER>>>.",
        "Placed CB Daryl Worley on Reserve/Injured; waived DE Damontre Moore.",
    ) == ('WAIVED_RELEASED', 'NOT_APPLICABLE_NOT_ROSTER_ELIGIBLE')


def test_inactive_requires_explicit_player_context():
    assert module.classify(
        'inactive_article',
        'The following players are inactive: WR <<<PLAYER>>>; TE Rob Gronkowski.',
        'WR Antonio Brown',
    ) == ('PROVABLY_ROSTER_ELIGIBLE_BEFORE_KICKOFF', 'EXPLICIT_INACTIVE')
    assert module.classify(
        'inactive_article',
        'The team has announced its inactives. The quarterback room includes <<<PLAYER>>> in the broader article.',
        'QB Jameis Winston is the backup quarterback today',
    ) == (None, None)


def test_chronology_is_fail_closed():
    kickoff = datetime.fromisoformat('2018-12-25T01:15:00+00:00')
    assert module.before_kickoff(None, '2018-12-23', kickoff, 'America/Los_Angeles') == (True, None)
    assert module.before_kickoff(None, '2018-12-24', kickoff, 'America/Los_Angeles')[0] is False
    assert module.before_kickoff(None, '2018-12-25', kickoff, 'America/Los_Angeles')[0] is False
    before = datetime(2018, 12, 25, 0, 45, tzinfo=timezone.utc)
    after = datetime(2018, 12, 25, 2, 0, tzinfo=timezone.utc)
    assert module.before_kickoff(before, None, kickoff, 'UTC') == (True, None)
    assert module.before_kickoff(after, None, kickoff, 'UTC')[0] is False


def test_transaction_ledger_date_and_alias_context():
    text = "12/23\nPlaced CB Daryl Worley on Reserve/Injured List; waived DE Damontre' Moore.\n"
    worley = module.player_contexts(text, ['Daryl Worley'])
    moore = module.player_contexts(text, ["Damontre' Moore"])
    assert len(worley) == 1 and len(moore) == 1
    wpos, wctx, wline = worley[0]
    mpos, mctx, mline = moore[0]
    assert module.ledger_date(text, wpos, 2018) == '2018-12-23'
    assert module.ledger_date(text, mpos, 2018) == '2018-12-23'
    assert module.classify('transaction_ledger', wctx, wline)[0] == 'RESERVE_IR'
    assert module.classify('transaction_ledger', mctx, mline)[0] == 'WAIVED_RELEASED'


def test_one_hop_discovery_is_same_domain_and_inactive_only():
    html = '''<html><body>
    <a href="/news/preview">Preview</a>
    <a href="/news/new-orleans-saints-inactives-vs-the-atlanta-falcons-x1971">New Orleans Saints inactives vs. the Atlanta Falcons</a>
    <a href="https://example.com/inactives">Inactives elsewhere</a>
    </body></html>'''
    soup = BeautifulSoup(html, 'html.parser')
    links = module.discover('https://www.neworleanssaints.com/sitemap/html/articles/2020/12', soup)
    assert links == ['https://www.neworleanssaints.com/news/new-orleans-saints-inactives-vs-the-atlanta-falcons-x1971']


def test_source_kind_transaction_detection():
    assert module.kind('https://www.raiders.com/team/transactions/2018') == 'transaction_ledger'
    assert module.kind('https://www.raiders.com/news/raiders-announce-transactions-12-24-18') == 'transaction_article'
    assert module.kind('https://www.jaguars.com/news/jaguars-make-roster-moves-x3605') == 'transaction_article'
    assert module.kind('https://www.chiefs.com/news/week-10-inactives-chiefs-vs-raiders') == 'inactive_article'


def test_no_weekly_status_authority_in_implementation():
    source = MODULE_PATH.read_text()
    forbidden = ['weekly_status', 'status_description_abbr', 'postgame snaps', 'play_by_play']
    for token in forbidden:
        assert token not in source.lower()
