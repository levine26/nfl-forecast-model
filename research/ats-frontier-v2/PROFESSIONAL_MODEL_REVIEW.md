# PROFESSIONAL MODEL REVIEW

The purpose of this review is to extract defensible public concepts, not reverse-engineer proprietary systems.

## nfelo

Public/reproducible enough to receive the highest practitioner weight. Key concepts: Elo/team-strength priors, QB adjustment, explicit market regression, spread/WP translation, CLV and market benchmarks. Most important lesson: a model should know when it is disagreeing with a powerful market and measure that disagreement rather than treating the market as one ordinary covariate.

## Dimers

Current public methodology describes more than 100 inputs and separate ML systems for margin and total, including quarterback, team efficiency, pace, rest/travel, weather and garbage-time adjustment. Useful confirmation that professional public systems model context and separate outcome targets. Exact feature engineering/fits are proprietary, so no hidden details are assumed.

## Fourth & Value

Current public materials are unusually explicit about multi-book odds, opposite-side fair-probability normalization, player/injury context and family-specific latent models. The transferable concept is market normalization and source/timestamp discipline, not any undocumented proprietary coefficients.

## ESPN FPI

Public methodology across generations consistently treats opponent-adjusted play efficiency and QB state as central. ESPN has described QB injury/backup adjustment as particularly challenging, and preseason versions have used market expectations and returning-starter/coordinator information. Later descriptions include unit-level pass/run and personnel components. Exact current model is proprietary.

## PFF power rankings / spread ratings

Public pages expose team and QB point-spread concepts and simulation-based predictions, supporting the idea that personnel/QB value should live on the same scale as market spread. Public methodology is not reproducible enough to transfer fitted values.

## Football Outsiders / FTN DVOA lineage

Core public concept: every play is compared with situation-specific league expectation and opponent strength; offense, defense and special teams can be separated. This supports situation/opponent adjustment and garbage-time awareness, but DVOA itself is not an ATS mechanism and proprietary weights should not be guessed.

## historical FiveThirtyEight NFL Elo

Transparent rating lineage with QB adjustments illustrates how a dynamic team-strength base and explicit quarterback state can coexist. Useful architecture context, not current professional evidence.

## Sagarin and Massey-style ratings

Long-running public rating systems confirm the robustness of opponent-adjusted comparative ratings, but limited disclosure and no demonstrated modern market-incremental ATS advantage make them benchmarks rather than candidate sources.

## David Sasser

Handled separately in `DAVID_SASSER_REVIEW.md`. Current public site evidence is college-football projection work, not a reproducible current NFL ATS methodology.

## Practitioner synthesis

Across the serious systems, the repeated ingredients are: market awareness, quarterback/player state, opponent/situation adjustment, dynamic updating, and calibrated probabilistic translation. None provides public evidence that “more football features” alone beat efficient NFL closing markets. Frontier V2 therefore takes the intersection of these concepts with academic evidence and prior LevLine failures rather than imitating any one product.