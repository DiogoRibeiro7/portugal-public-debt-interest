# Comparator Panel Design

The default comparator panel is the euro-area country universe, not a discretionary selection of nearby or high-debt countries. It includes the twenty euro-area members represented at the configured endpoint year: Austria, Belgium, Croatia, Cyprus, Estonia, Finland, France, Germany, Greece, Ireland, Italy, Latvia, Lithuania, Luxembourg, Malta, the Netherlands, Portugal, Slovakia, Slovenia, and Spain.

The panel also retains `EA20` and `EU27_2020` aggregate rows for reference. These aggregates are marked with `is_aggregate = true` and are excluded from country ranks and cross-sectional country counts.

This design keeps the comparison defensible: every country row is drawn from the same Eurostat concepts and the inclusion rule is institutional membership rather than outcome-based selection.
