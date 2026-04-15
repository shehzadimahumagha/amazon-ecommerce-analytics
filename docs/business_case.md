# Business Case: E-Commerce Growth Analytics

## Project Title
**E-Commerce Growth Analytics: RFM Segmentation, A/B Experiment Analysis, and Predictive CLV Modeling**

---

## Problem Statement

A mid-size e-commerce marketplace (modelled on the Olist platform) is growing top-line revenue but facing an inefficient marketing spend problem. The business has no framework to distinguish high-lifetime-value customers from one-time buyers, resulting in uniform promotional investment across the entire customer base.

Key symptoms observed:
- ~97% of customers place only one order (single-purchase rate is extremely high)
- Marketing budget is allocated uniformly — no CLV-based targeting
- Free-shipping promotions are offered without measuring impact on AOV or retention
- No segment-level understanding of which product categories attract high-value customers

---

## Business Objective

Build a customer analytics pipeline that enables the marketing team to:

1. **Segment** customers by predicted lifetime value (RFM + CLV model)
2. **Quantify** the revenue impact of free-shipping promotions via A/B analysis
3. **Identify** which product categories serve as high-LTV customer entry points
4. **Recommend** where to concentrate retention spend and how to define tier-based marketing programmes

---

## Target Stakeholders

| Stakeholder | Use of this analysis |
|---|---|
| VP Marketing | Budget allocation by CLV tier, segment targeting |
| Growth / CRM Team | Retention campaign triggers, win-back sequencing |
| Product Team | Category-level LTV index for inventory / merchandising decisions |
| Finance | Revenue forecasting using probabilistic CLV |

---

## Success Metrics (KPIs)

| KPI | Definition | Target |
|---|---|---|
| 90-Day Retention Rate | % of first-time buyers placing a 2nd order within 90 days | Baseline + improvement opportunity identified |
| 12-Month Historical CLV | Total revenue per customer in first 12 months | Segmented by tier; Pareto validation |
| Predicted CLV (12m) | BG/NBD + Gamma-Gamma forward forecast | Accuracy vs. held-out historical data |
| A/B Lift (AOV) | % change in avg order value: free shipping vs. paid | Statistical significance at α=0.05 |
| Revenue Concentration | % of revenue from top 20% of customers | Pareto (80/20) validation |
| Category LTV Index | Median CLV ratio: category X vs. overall baseline | Identify top 5 entry-point categories |

---

## Assumptions

1. **Customer identity**: We use `customer_unique_id` as the stable identifier across orders. Olist's actual repeat customer identification uses zip code + name matching, but `customer_unique_id` is reliable within this dataset.

2. **Revenue definition**: `payment_value` (from the payments table) is used as net order revenue. This includes instalment payments credited at purchase time and excludes returns (which are not tracked in this dataset version).

3. **Analysis period**: The primary analysis window is January 2017 – August 2018, covering the period of stable order volume. The 2016 data (partial year) is excluded from trend analysis but retained for cohort construction.

4. **A/B experiment proxy**: The experiment is constructed from observational data (free-shipping orders vs. paid-shipping orders). This is an observational design, not a true RCT. Confounders are controlled via regression. All conclusions are framed as correlational unless the regression-adjusted estimates align with the naive t-test.

5. **CLV horizon**: We estimate CLV over a 12-month forward window. For customers with < 4 weeks of tenure, CLV estimates are less reliable and are flagged.

---

## Scope Exclusions

- Real-time scoring pipeline (out of scope for a static portfolio project)
- Seller-side analytics (focus is customer-side)
- Geographic/geolocation deep-dive (available in the data but not the core thesis)
