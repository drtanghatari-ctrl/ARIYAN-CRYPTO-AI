# A005 amendment: single holdout run (committed BEFORE any holdout result was computed)

A005's protocol said the holdout stays locked. A005 then passed all six development marks, which is the condition under
which the earlier family protocols (A001/A004) allow exactly one holdout run of the single best candidate. The holdout is
12 months (2025-11-01 to 2026-10-31) that no study, diagnostic or tuning decision has touched, so it is far stronger evidence
than waiting 99 days for A006. This amendment authorises that one run and nothing else. It is a change to my own earlier
commitment, made before seeing any holdout number, and it is recorded here so it can be audited.

Candidate: top 10 by volume with spot, hurdle 2 bp/day (the A005 best). Costs as in A005.
Marks (all required, same as A006): 1) net return > 0; 2) max drawdown no deeper than 3%; 3) positive with all costs doubled;
4) net return beats cash at 4% a year over the 365-day window.
Single use (`scripts/run_a005_holdout.py` refuses a second run). Outcome: PASS keeps A006 running and lifts confidence only slightly
(one year, edge already decaying); FAIL closes this harvest design before A006 even finishes. Either way the holdout is then spent.
