# LevLine UX Benchmark Notes

Status: research only. These are interaction/hierarchy references, not templates to copy.

## Forecasting products

| Reference | Useful pattern | LevLine translation | What not to copy |
| --- | --- | --- | --- |
| FiveThirtyEight NFL | Win probability is the primary object; team strength/methodology are separate deeper layers; forecast history is integral to the product | Keep official LevLine probability visually dominant; separate Power/Methodology; make receipts/accountability a first-class destination | Do not revive Elo/QB mechanics merely because the old product used them; our model evidence governs architecture |
| ESPN Matchup Predictor | Extremely fast visual answer to “who is favored?” | Preserve instant scanability on weekly cards | Do not reduce LevLine to an unexplained percentage or copy ESPN branding/layout |
| Opta Analyst | Probability plus concise written interpretation around a matchup | Use one compact factual interpretation and a disciplined `What changed` block | Avoid editorial volume that pushes provenance/lock semantics out of view |
| Metaculus | Probability itself is the confidence statement; track record/calibration is public; forecast changes over time are meaningful | Add calibration/accountability, probability-band performance and receipt history; show change without categorical confidence labels | LevLine is not a crowd forecasting platform; no user prediction mechanics are needed |
| Polymarket sports view | Compact probability/line/total market state and real-time movement are easy to scan | Useful reference for a *separate* market-pulse subview and compact movement display | Do not make Sunday Signal look like a trading/betting terminal; no bet/EV CTAs or profit colors |

## Product principles supported by the benchmark review

### 1. Probability first

A game card succeeds if the user can identify LevLine's side and probability almost instantly. Secondary quantities should not have equal typographic weight.

### 2. Track record is not a W-L badge

A serious probability product should expose calibration, Brier/log loss and sample size. Winner accuracy may remain visible but should not dominate probability-quality measures.

### 3. Change is information

A returning user needs to see what moved since the last meaningful snapshot, not just the current state. LevLine can make this especially trustworthy because it already has immutable lock and run-history concepts.

### 4. Context needs provenance

News, personnel, weather and market movement should carry their own timestamps/source state. Context appearing near a probability move does not imply causation.

### 5. Expert depth belongs behind the first answer

Progressive disclosure is the right architecture for movement, model components, source health and methodology. Experts can access all of it without forcing every user to parse it on the weekly board.

## LevLine-specific opportunities

### “Since your last visit”

Store the last-viewed forecast snapshot per game in local browser storage. On return, show a compact factual delta such as `LevLine +1.8 pp · Market +0.6 pp · depth-chart change detected`. This requires no account and no paid backend.

### Slate controls

Default sort remains kickoff time. Optional lightweight controls can expose:
- biggest LevLine/market disagreement;
- largest forecast move;
- locked vs live forecasts;
- team search/filter.

These are navigation tools, not betting recommendations.

### Shareable receipt

Every game should have a durable URL and a share action that includes the official probability, lifecycle (`Live` or `Final pregame`) and lock timestamp when applicable. For GitHub Pages, research static/hash/query routing that survives direct navigation without requiring a paid server.

### Game dossier navigation

On long mobile game pages, use a sticky summary plus in-page section navigation (`Forecast`, `Changes`, `Context`, `Movement`, `Sources`) rather than a giant uninterrupted modal.

### Data-health transparency

A small `Data as of` control should summarize freshness without cluttering the main forecast. Degraded inputs must be visible and explanatory; a stale feed must not look equivalent to a fresh one.

### Conditional context modules

Do not render weather just because weather data exists. Outdoor/retractable-roof games with materially relevant wind/precipitation/temperature earn a weather module; otherwise omit it. Apply the same principle to personnel and market dispersion.

### Responsible precision

Approximate score and probability-implied line should visually read as downstream translations. Do not display unnecessary decimal precision. The official winner probability remains the strongest quantitative claim.

## Research metrics for UI prototypes

Without adding paid analytics, Playwright/local instrumentation can test objective properties:
- first-contentful payload size / number of initial data requests;
- time until official probability appears in a controlled build;
- DOM/visual order of official probability versus secondary numbers;
- keyboard reachability and focus return;
- no horizontal overflow at 320/390/768/1180/1440 widths;
- direct-route recovery for a game URL;
- behavior under missing/stale market, context and impact payloads;
- reduced-motion behavior;
- text equivalent for movement charts.

Qualitative user testing can then answer the primary comprehension questions: who is favored, how likely, what changed, and whether the forecast is live or locked.

## Reference links

- FiveThirtyEight NFL methodology: https://fivethirtyeight.com/methodology/how-our-nfl-predictions-work/
- Metaculus forecasting guide: https://www.metaculus.com/how-to-forecast/
- Metaculus track record: https://www.metaculus.com/questions/track-record/
- Polymarket NFL view: https://polymarket.com/sports/nfl

No reference above authorizes a data source or model feature; they are product/interaction benchmarks only.
