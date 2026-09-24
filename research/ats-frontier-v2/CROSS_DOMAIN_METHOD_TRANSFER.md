# CROSS DOMAIN METHOD TRANSFER

Cross-domain methods are admissible only when both transfer logic and failure modes are explicit.

## Weather forecasting

### Transferable
- Proper scoring rules and CRPS/log-score selection.
- Calibration + sharpness as separate forecast qualities.
- Ensemble model output statistics / distributional post-processing.
- GAMLSS, distributional forests and quantile approaches for heteroskedastic predictive distributions.
- Forecast combination with recalibration rather than naive averaging.

### Why it may transfer
Weather, like NFL margin forecasting, is a noisy probabilistic problem where uncertainty varies by state and point predictions are insufficient.

### Why it may fail
Weather ensembles contain many physics-based members and enormous sample grids; NFL has only hundreds of games per season. Methods requiring rich ensemble diversity or massive samples can overfit badly.

## Finance / market microstructure

### Transferable
- latent fair value inferred from multiple noisy quotes;
- price discovery / lead–lag;
- dispersion as uncertainty;
- event studies around information arrival;
- state-space filtering of dynamic latent value;
- stale-quote detection and quote-age weighting.

### Why it may transfer
Sportsbook lines and prices are market quotes produced by competing market makers and bettor information aggregation.

### Why it may fail
Sportsbook payoff structure is discrete, markets are lower-frequency and bookmaker objectives include risk/hold/customer segmentation. “Sharp book” labels can be unstable and data feeds may synchronize mechanically.

## Soccer

### Transferable
- dynamic offense/defense latent strengths;
- Bayesian hierarchical shrinkage;
- bivariate/joint score models;
- time-decay/state-space team strength;
- market-calibrated probability comparison.

### Why it may transfer
Both are team sports with time-varying latent ability and paired competition.

### Why it may fail
NFL scoring is a discrete drive/possession lattice with far fewer games and radically different scoring increments. Direct Poisson parameterization is inappropriate.

## Baseball / basketball

### Transferable
- hierarchical player effects and replacement value;
- lineup availability and starter probabilities;
- player-absence event studies;
- shrinkage for backups/small samples;
- calibrated possession/play-level value aggregation.

### Why it may transfer
Player availability and replacement quality are common causal drivers of team strength.

### Why it may fail
Football roles are highly interdependent, participation is sparse, and many positions have weak individually identifiable public effects.

## Cross-domain conclusion

The strongest transfers are **methodological disciplines**—state-space filtering, hierarchical shrinkage, proper scoring, calibration, event-timed price discovery—not domain-specific fitted coefficients. No cross-domain method is itself a Frontier candidate.