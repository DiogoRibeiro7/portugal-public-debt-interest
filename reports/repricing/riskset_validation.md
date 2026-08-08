# Repricing panel validation

Rows: 496. Instrument classes: 2.

## Checks

| Check | Passed | Severity | Detail |
| --- | --- | --- | --- |
| unique_class_period | True | error | 0 duplicated instrument-class months |
| non_negative_exposure | True | error | 0 negative exposures |
| stock_flow_closure | True | error | largest opening-plus-flow residual 0.000000 EUR million |
| positive_outstanding_value_change_share_in_range | True | warning | positive outstanding-value change share spans 0.0000 to 0.5846 |
| coverage_reported | True | info | savings_certificates: 2001-02-28..2026-06-30 n=305; treasury_certificates: 2010-08-31..2026-06-30 n=191 |

## Reconciliation to the burden paper's debt stock

IGCP State direct debt and Maastricht general-government debt are different concepts, so a gap is expected. It is reported per year rather than asserted away.

| Year | IGCP (EUR m) | Maastricht (EUR m) | Difference | % of Maastricht |
| --- | --- | --- | --- | --- |
| 2001 | 72,450 | 77,908 | 5,458 | 7.0% |
| 2002 | 79,475 | 85,527 | 6,052 | 7.1% |
| 2003 | 83,377 | 93,321 | 9,944 | 10.7% |
| 2004 | 90,739 | 102,155 | 11,416 | 11.2% |
| 2005 | 101,758 | 114,543 | 12,785 | 11.2% |
| 2006 | 108,557 | 122,467 | 13,910 | 11.4% |
| 2007 | 112,804 | 127,571 | 14,767 | 11.6% |
| 2008 | 118,463 | 135,209 | 16,746 | 12.4% |
| 2009 | 132,746 | 153,624 | 20,878 | 13.6% |
| 2010 | 151,775 | 179,653 | 27,878 | 15.5% |
| 2011 | 174,895 | 201,044 | 26,149 | 13.0% |
| 2012 | 194,466 | 216,747 | 22,281 | 10.3% |
| 2013 | 204,252 | 223,313 | 19,061 | 8.5% |
| 2014 | 217,126 | 229,391 | 12,265 | 5.3% |
| 2015 | 226,363 | 235,046 | 8,683 | 3.7% |
| 2016 | 236,283 | 244,495 | 8,212 | 3.4% |
| 2017 | 238,263 | 246,399 | 8,135 | 3.3% |
| 2018 | 245,558 | 248,277 | 2,719 | 1.1% |
| 2019 | 251,012 | 249,044 | -1,969 | -0.8% |
| 2020 | 268,316 | 269,578 | 1,261 | 0.5% |
| 2021 | 278,490 | 268,188 | -10,301 | -3.8% |
| 2022 | 287,019 | 271,358 | -15,662 | -5.8% |
| 2023 | 295,952 | 261,889 | -34,063 | -13.0% |
| 2024 | 305,710 | 270,902 | -34,808 | -12.8% |
| 2025 | 315,237 | 275,063 | -40,175 | -14.6% |
