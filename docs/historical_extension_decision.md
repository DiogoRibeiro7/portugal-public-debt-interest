# Historical Extension Decision

The principal analytical sample is the harmonised Eurostat ESA 2010 series from 1995 onward. Pre-1995 AMECO rows are retained only when the linked source provides the core quantities required to reconstruct interest expenditure, nominal GDP, debt, and the corresponding ratios.

Rows before 1995 are therefore not padded into the processed analytical table. If an AMECO archive supplies only metadata or all-missing values for the configured years, those rows are excluded from the main output rather than appearing as observations with missing fiscal quantities.

This decision treats the linked AMECO extension as contextual evidence, not as accounting-equivalent continuation of the Eurostat sample. The annual table carries `is_harmonised_main_sample` and `is_historical_extension` flags so analysis can separate the authoritative sample from any retained historical extension.
