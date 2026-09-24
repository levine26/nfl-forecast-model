# MARKET DOMINANCE FORENSICS

# Why is the sportsbook currently beating LevLine?

This is an evidence-ranked diagnosis, not a claim about sportsbook motives or proprietary methods.

## 1. The market aggregates richer and timelier player/QB information — **strong evidence**

**Facts:** closing/sequential lines generally contain more information than earlier lines; player-absence biases can be reduced by close; public professional systems devote substantial modeling effort to QB and personnel state; prior LevLine standalone football models lose to market.  
**Inference:** the market likely integrates injury/starter/role information more effectively and/or earlier than LevLine's compressed historical team-state features.  
**Action:** M2 must target timestamped uncertainty and replacement value relative to the already-moved market, not generic injury effects.

## 2. LevLine's historical market representation is impoverished — **strong/moderate evidence**

**Fact:** prior LevLine research uses a historical schedule spread whose exact observation horizon is opaque; a single spread omits book disagreement, side price, moneyline, total and movement path. External providers can preserve timestamped multi-book quote paths. Adaptive Candidate 3 also showed simple path information collapses toward market level.  
**Inference:** a dynamic latent market state may contain useful information that the current static representation discards.  
**Action:** M1 is the first data-investment priority.

## 3. Candidate search/selection noise has created false-looking positives — **strong evidence**

**Fact:** Adaptive Candidate 1 looked favorable in 2025 alone (+3 winners) despite strongly negative full-development evidence; Candidate 2/3 gains were each +1 winner and fragile/event-concentrated; Candidate 5 changed zero winners.  
**Inference:** small-sample selection can easily manufacture attractive ATS headlines.  
**Action:** proper scores + uncertainty + preregistration dominate ATS headlines; no rescue/tuning after results.

## 4. LevLine temporal-state representation is too coarse — **moderate evidence**

**Fact:** fixed rolling summaries do not explicitly model latent evolving strength, process noise or regime changes; state-space sports literature does.  
**Inference:** M3 may improve representation during structural changes.  
**Counterpoint:** the market may already be a better dynamic estimator, so this is less information-novel than M1/M2.

## 5. Uncertainty/distribution representation is misspecified — **moderate evidence**

**Fact:** ATS requires mass around a line and explicit pushes; Q2's finite support failed structurally; Q1/Q3 did not improve market-relative proper scores.  
**Inference:** LevLine can improve probability correctness with a tail-safe discrete/heteroskedastic representation, but distributional modeling alone is unlikely to generate edge.  
**Action:** M4 survives as representation research, not alpha presumption.

## 6. The market behaves like an ensemble of heterogeneous analysts/bettors — **moderate evidence**

**Fact:** literature documents information arrival and informed trading patterns; sportsbooks aggregate many participants and competing books.  
**Inference:** a single public model must find genuinely orthogonal information to outperform that aggregate.  
**Action:** combination inside LevLine is not enough unless components demonstrate residual diversity.

## 7. Matchup interactions are missing — **weak/unknown evidence**

Pressure, OL/pass-rush, coverage, PROE and pace interactions are football-real. Phase 1 found no strong evidence that a broad interaction learner would remain incremental after market conditioning.  
**Action:** do not create a matchup feature tournament. Individual interactions may enter M3 only if preregistered from a mechanism and sample-feasible.

## Overall diagnosis

The dominant failure is **not insufficient algorithm sophistication**. It is the combination of (a) competing against a very informative market with substantially the same public football information, (b) using a compressed/static representation of the market and player state, and (c) drawing conclusions from a tiny number of switched ATS decisions. Frontier V2 therefore spends its next effort on better information clocks and state reconstruction before fitting anything.