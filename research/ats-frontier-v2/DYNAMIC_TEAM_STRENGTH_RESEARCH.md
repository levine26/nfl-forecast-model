# DYNAMIC TEAM STRENGTH RESEARCH

## Hypothesis

Fixed rolling averages treat a team's recent games as exchangeable observations inside an arbitrary window. NFL team/unit strength is more plausibly a latent process that evolves continuously, occasionally jumps, and is observed with substantial game-level noise.

`FRONTIER-M3-HIERARCHICAL-STATE` asks whether a sample-efficient dynamic latent state contains market-incremental information after contemporaneous market conditioning.

## Literature transfer

- Glickman & Stern directly modeled NFL team strength as an autoregressive state process, separating week-to-week injury/random change from season-to-season personnel change.
- Soccer state-space work by Crowder et al., Koopman/Lit and modern Bayesian authors shows dynamic offense/defense strengths can be estimated with partial pooling and non-Gaussian observations.
- Dynamic Bradley–Terry/Elo/Glicko literature formalizes evolving paired-comparison skill and uncertainty.
- Recent Bayesian change/shrinkage work provides a route to occasional abrupt state moves without allowing every noisy game to become a regime change.

## Proposed state decomposition

A future architecture may include latent:

- offense pass / rush state;
- defense pass / rush state;
- QB state (shared or linked with M2);
- OL / receiving / pass-rush / coverage unit states only if coverage supports them;
- special-teams state where sample size allows;
- home/travel/rest context as observation effects rather than persistent team skill.

Partial pooling and explicit process noise are mandatory. Team-week state must be updated only by games and information available before the target game.

## What is genuinely different from A0/C0

M3 is not “another team rating.” It must replace fixed-window compression with a coherent latent process, uncertainty and potentially change-point behavior. It is still the least information-novel shortlist item; if it cannot outperform a market-conditioned dynamic baseline in historical development it should die immediately rather than be rescued with more features.

## Key ablation questions for a future preregistration

- dynamic latent state vs frozen rolling summaries;
- offense/defense decomposition vs one team strength;
- process noise fixed vs hierarchical;
- changepoint mechanism on/off;
- QB state on/off while controlling for M2 to avoid double counting;
- market residual target vs standalone margin target.

## Failure risks

- The market may already be a better real-time state estimator.
- NFL has few games per team; overly rich latent decomposition is weakly identified.
- State-space flexibility can silently overfit process noise/changepoints.
- Historical team data may be clean while roster/coach transition timing remains ambiguous.

## Phase-1 status

**SURVIVES, medium priority.** It is scientifically stronger than fixed windows but less likely than M1/M2 to create new conditional information.