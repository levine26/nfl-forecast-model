from __future__ import annotations

"""Independent, fail-closed human Read quality checks.

Shared by focused game validation and the final full-slate gate. This is NOT a
substitute for checking original reporting or verifying every factual claim.
It catches structural low-information prose that lexical seven-grams miss.
Research-only: no forecast/model features are read or written here.
"""

import re

STOCK_PATTERNS = (
    (r"\bcenters on\b", "mechanical matchup opening"),
    (r"\b(?:that|this) detail changes\b", "interchangeable causal assertion"),
    (r"\bcan exploit it only by forcing\b", "mechanically stitched conclusion"),
    (r"\bthe relevant opponent.side profile\b", "anonymous statistical backdrop"),
    (r"\bthe passing.game backdrop\b", "stock statistical transition"),
    (r"\blevline does not make up\b", "internal model caveat in human reporting"),
    (r"\bdeserves the first paragraph\b", "writer-process language"),
    (r"\bcoverage highlights\b", "database-label prose"),
    (r"\bpressure note\b", "database-label prose"),
    (r"\bhistory note\b", "database-label prose"),
    (r"\bthe cleanest lens\b", "stock analytical framing"),
    (r"\bturn manageable series into\b", "reusable generic analysis"),
    (r"\b(?:achilles levline|market gap:)\b", "malformed editorial stitching"),
)
TACTICAL_FAMILIES = {
    "passing": r"\b(?:quarterback|passing|pass game|dropbacks?|pocket|receivers?|routes?|throw(?:ing|s)?|downfield|tight ends?)\b",
    "protection": r"\b(?:protection|pass.rush|rushers?|blitz|pressure|sacks?|offensive line|tackles?)\b",
    "coverage": r"\b(?:coverage|secondary|cornerbacks?|safet(?:y|ies)|man.coverage|zone.coverage)\b",
    "running": r"\b(?:rushing|running|run game|ground game|backs?|linebackers?|run defense)\b",
    "explosive": r"\b(?:explosive|deep ball|big.play|chunk.play|vertical|red.zone|downfield)\b",
    "scheme": r"\b(?:motion|play.action|screen(?:s)?|coordinators?|scheme|formations?|alignments?|press coverage)\b",
}
ACTION = re.compile(
    r"\b(?:attack|punish|challenge|counter|exploit|stress|force|limit|contain|"
    r"disrupt|protect|adjust|blitz|rush|throw|block|run|cover|stretch|press|"
    r"pressure|isolate|lean|target|hold|create|prevent|explore|test|handle|"
    r"feed|leaning|stretching|sustain|sustaining|convert|turn)\w*\b",
    re.I,
)
INTERACTION = re.compile(
    r"\b(?:against|versus|while|but|because|if|unless|whereas|which|"
    r"counter|forces?|struggles? with|tests?|when)\b",
    re.I,
)
MODEL_LEAKAGE = re.compile(
    r"\b(?:levline|f[-–—]st|pure model|moneyline|probability.implied|
    r"market gap|vig.free|expected.margin)\b",
    re.I,
)


def assess_human_read(headline: str, paragraph: str) -> list[str]:
    """Return evidence-backed review failures; no silent prose reconstruction.

    Checks structural mechanisms, causal interaction, writer-process leakage,
    and known mechanically stitched patterns. Distinct names and verified
    citations are enforced separately by the existing focused validator.
    """
    text = re.sub(r"\s+", " ", str(paragraph or "")).strip()
    heading = re.sub(r"\s+", " ", str(headline or "")).strip()
    issues: list[str] = []
    for pattern, reason in STOCK_PATTERNS:
        if re.search(pattern, text, flags=re.I) or re.search(pattern, heading, flags=re.I):
            issues.append(reason)
    if MODEL_LEAKAGE.search(text):
        issues.append("model or betting commentary contaminated the human paragraph")
    families = [
        name for name, pattern in TACTICAL_FAMILIES.items()
        if re.search(pattern, text, flags=re.I)
    ]
    if len(families) < 2:
        issues.append(f"insufficient distinct tactical mechanisms: {families}")
    if len(ACTION.findall(text)) < 2 or not INTERACTION.search(text):
        issues.append("no concrete tactical action-and-counteraction explanation")
    if re.search(r"\b(?:the|this) (?:game|matchup) (?:will|could|may) (?:come down to|be decided by)\b", text, re.I):
        if len(families) < 3:
            issues.append("reusable generic matchup conclusion without distinct evidence")
    return issues
