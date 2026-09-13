from __future__ import annotations

from research.v09b_modern_dnp_bbox_parser_v2 import (
    dnp_blocks_from_bbox_pages,
    parse_dnp_tokens_from_bbox_pages,
)


def _line(left: str = "", right: str = "", *, width: float = 1200.0, y: float = 100.0):
    words = []
    for side, text in (("left", left), ("right", right)):
        if not text:
            continue
        x = 70.0 if side == "left" else width / 2.0 + 70.0
        for part in text.split():
            word_width = max(10.0, len(part) * 5.0)
            words.append(
                {
                    "text": part,
                    "x_min": x,
                    "x_max": x + word_width,
                    "y_min": y,
                    "y_max": y + 10.0,
                }
            )
            x += word_width + 5.0
    return {"y_min": y, "x_min": min(word["x_min"] for word in words), "words": words}


def _pages(*lines):
    return [{"page_number": 1, "width": 1200.0, "height": 1600.0, "lines": list(lines)}]


def test_bbox_parser_recovers_full_oakland_dnp_line():
    pages = _pages(
        _line("Did Not Play", "Did Not Play", y=100),
        _line(
            "QB 9 K.Hogan, G/C 74 N.Falah",
            "QB 2 A.McCarron, CB 20 D.Worley, DE 56 D.Moore, G 63 C.Hunt",
            y=120,
        ),
        _line("Not Active", "Not Active", y=140),
    )
    tokens = parse_dnp_tokens_from_bbox_pages(
        pages,
        season=2018,
        week=16,
        game_id="2018_16_DEN_OAK",
        away_team="DEN",
        home_team="OAK",
    )
    observed = {(t.team, t.jersey_number, t.gamebook_name) for t in tokens}
    assert ("OAK", "20", "D.Worley") in observed
    assert ("OAK", "56", "D.Moore") in observed
    assert ("OAK", "63", "C.Hunt") in observed
    assert ("DEN", "9", "K.Hogan") in observed


def test_bbox_parser_keeps_wrapped_brown_out_of_washington_column():
    pages = _pages(
        _line("Did Not Play", "Did Not Play", y=100),
        _line(
            "CB 5 R.Sherman, QB 11 B.Gabbert, G 64 A.Stinnie, OL 70 R.Hainsey, WR 81",
            "",
            y=120,
        ),
        _line("A.Brown", "QB 8 K.Allen, OL 76 S.Cosmi", y=130),
        _line("Not Active", "Not Active", y=140),
    )
    blocks = dnp_blocks_from_bbox_pages(pages)
    assert "A.Brown" in blocks["left"]
    assert "K.Allen" not in blocks["left"]
    tokens = parse_dnp_tokens_from_bbox_pages(
        pages,
        season=2021,
        week=10,
        game_id="2021_10_TB_WAS",
        away_team="TB",
        home_team="WAS",
    )
    observed = {(t.team, t.jersey_number, t.gamebook_name) for t in tokens}
    assert ("TB", "81", "A.Brown") in observed
    assert ("WAS", "8", "K.Allen") in observed
    assert ("WAS", "76", "S.Cosmi") in observed
    assert ("TB", "8", "K.Allen") not in observed
    assert all(t.gamebook_name != "QB" for t in tokens)


def test_bbox_parser_fails_closed_without_both_column_headings():
    pages = _pages(
        _line("Did Not Play", "", y=100),
        _line("99 K.Saunders", "81 A.Brown", y=120),
        _line("Not Active", "Not Active", y=140),
    )
    try:
        dnp_blocks_from_bbox_pages(pages)
    except ValueError as exc:
        assert "right" in str(exc)
    else:
        raise AssertionError("missing right-side DNP heading must fail closed")
