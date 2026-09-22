# Candidate 3 preregistration addendum — final pre-kickoff market control

Status: **pre-target-result reporting-contract clarification**

Original frozen preregistration commit: `97a974228f202b6dcfb1ec4f72267d6e7216774b`

No Candidate 3 model definition changes are made by this addendum.

The original preregistration named:
- frozen F-ST;
- raw lock-band market;
- market-path-without-F-ST;
- component-resolved;
- Candidate 1 unchanged;
- naïve weekly refit unchanged;
- Candidate 2 unchanged;
- lambda=0 ablation.

The user also explicitly required a **final market only** control. That control is added here before Candidate 3 target scoring:

- **final_prekickoff_market**: for each sportsbook, use the latest qualifying h2h snapshot strictly before kickoff; construct the same proportional two-outcome no-vig home probability; aggregate across available sportsbooks using the logistic of the median book logit. This is a descriptive control only.
- It is not used in Candidate 3 feature construction, lambda selection, sample selection, missingness rules, robustness-grid selection, or success/disposition rules.
- It may contain information later than Candidate 3's primary lock band, so it is explicitly labeled a later-horizon control and is never treated as a same-horizon comparator.
- Post-kickoff prices remain prohibited.

Everything else in `ADAPTIVE_WEEKLY_CANDIDATE3_PREREGISTRATION.json` remains frozen and unchanged.
