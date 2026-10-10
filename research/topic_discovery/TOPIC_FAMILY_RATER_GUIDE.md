# Topic Family Validation Guide

## Purpose

This audit validates whether headlines belong to economically coherent,
continuing topic discourses. It does not measure sentiment and does not require
two headlines to report the same immediate incident.

Do not use market prices, article text, publication source, dates, search, or
other raters' answers. Judge from the supplied headline only.

## Headline Assignment Sheet

For each headline, enter:

- `primary_topic`: exactly one allowed topic code, or `other_unclear`.
- `secondary_topics`: optional additional topic codes separated by `|`.
- `topic_centrality`: `central`, `material_secondary`, `incidental`, or
  `unclear`.
- `confidence`: `high`, `medium`, or `low`.
- `reviewer_notes`: optional short explanation.

Choose a topic when the headline is recognizably part of that continuing
economic or geopolitical discourse, even if it covers a different sub-event or
perspective from other headlines in the topic.

## Pair Sheet

For each pair, enter:

- `same_topic_discourse`: `yes`, `no`, or `unclear`.
- `confidence`: `high`, `medium`, or `low`.
- `reviewer_notes`: optional short explanation.

Use `yes` when both headlines can reasonably contribute perspectives to the
same named continuing topic during a common time window. They need not describe
the same incident. Shared generic words, countries, people, or the fact that
both concern politics are not sufficient.

## Allowed Topic Codes

| Code | Meaning |
| --- | --- |
| `monetary_policy` | Central-bank decisions, guidance, policy rates, and balance sheets |
| `inflation_prices` | Consumer/producer prices, inflation, and cost-of-living pressure |
| `labor_markets` | Employment, unemployment, wages, hiring, layoffs, and broad labor conditions |
| `growth_recession` | Growth, recession, aggregate demand, production, and the business cycle |
| `fiscal_tax_debt` | Budgets, taxes, public spending, deficits, and sovereign debt |
| `banking_credit` | Bank health, lending conditions, credit stress, and financial stability |
| `corporate_earnings_deals` | Firm earnings, guidance, mergers, acquisitions, and offerings |
| `market_performance` | Observed broad market movements, yields, volatility, or positioning |
| `energy_oil_gas` | Oil/gas supply, prices, OPEC, and energy security |
| `technology_ai_chips` | AI, semiconductors, major technology regulation, and cybersecurity |
| `trade_tariffs` | Tariffs, trade restrictions, export controls, and supply chains |
| `covid_pandemic` | COVID health policy, vaccines, restrictions, and consequences |
| `russia_ukraine` | Russia-Ukraine war and its military, political, sanctions, energy, and humanitarian consequences |
| `israel_gaza` | Israel-Gaza war, Hamas, hostages, ceasefires, and humanitarian consequences |
| `iran_israel` | Direct/proxy Iran-Israel confrontation and escalation risk |
| `red_sea_houthi` | Houthi attacks, responses, and Red Sea shipping disruption |
| `us_china_relations` | Strategic, economic, diplomatic, or military U.S.-China competition |
| `climate_transition` | Climate policy, carbon regulation, and the energy transition |
| `other_unclear` | No listed family is defensible from the headline alone |

Use `other_unclear` for isolated domestic politics, culture, crime, sport,
personal profiles, and one-off stories without a listed continuing economic
topic. Do not invent a new code in the audit sheet; propose it in
`reviewer_notes` if a recurring missing family becomes apparent.

## Human Verification Of The Agent Audit

The human verification sheets preserve the agent judgment in `agent_*` columns.
For every row, enter:

- `human_decision = accept` when the agent judgment is suitable as written;
- `human_decision = correct` and complete all relevant `corrected_*` fields when
  the judgment should change;
- `human_decision = unclear` when the human cannot resolve the headline from
  the available text.

Add `human_confidence` as `high`, `medium`, or `low`. Correction fields should
remain blank for accepted rows. Do not open the hidden key while verifying.
