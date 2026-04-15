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

---

## Key Findings

*Numbers derived from outputs/tables/ after running notebooks 01–05.*

### Scale and Baseline
- **96,477 delivered orders** across 93,357 unique customers (Oct 2016 – Aug 2018)
- **Total revenue: R$15,422,462** | AOV: R$159.86 | Median order: R$105.28
- **97% of customers placed only one order** — repeat purchase rate is 3.00%

### Retention
- **M1 cohort retention: 0.48%** — fewer than 1 in 200 customers places a second order within their first month
- **M3 cohort retention: 0.25%** — retention continues falling steeply and plateaus below 0.3% by month 3
- The critical re-engagement window is the **first 30 days** after acquisition

### Customer Segmentation (RFM)
- **Champions (6.9% of customers) drive 13.1% of revenue** — avg order value R$312 vs. R$160 platform average
- **Loyal Customers** is the largest segment (29.1% of customers, 23.7% of revenue)
- RFM segments align with CLV tiers, confirming RFM is a valid operational proxy for predicted LTV

### CLV Concentration (Pareto)
- **Platinum tier (25.0% of customers) generates 59.2% of revenue** (avg CLV: R$390.70)
- Bottom 50% (Bronze + Silver tiers) accounts for only 19.3% of revenue
- Revenue concentration significantly exceeds a classic 80/20 split — the top quartile captures nearly 60%

### Free-Shipping Experiment
- Free-shipping orders show **−30.2% lower revenue per order** vs. paid-shipping (t-test p < 0.0001, Cohen's d = −0.301)
- **Regression-adjusted ATE: −R$22.59 per order** (OLS with HC3 robust errors, R² = 0.908)
- Free-shipping orders score **+0.23 pts higher on review scores** (p = 0.0002), suggesting a satisfaction benefit even where AOV is lower
- Finding is from observational data; a randomised trial with an AOV threshold is recommended before policy change

### Delivery & Satisfaction
- **Avg delivery: 12.1 days** | Median: 10 days
- **Review score drops 2.26 points** from the fastest delivery bin (1–5 days: 4.43/5) to the slowest (31–60 days: 2.17/5)
- Delivery speed is a direct, measurable lever on customer satisfaction and downstream retention probability

### Entry Category & Loyalty
- **home_appliances has the highest repeat rate at 8.74%** — nearly 3× the platform average
- Other high-repeat entry categories: fashion_male_clothing (6.93%), furniture_bedroom (6.10%), fashion_bags_accessories (5.88%)
- Acquisition campaigns targeting high-retention entry categories produce customers with structurally higher predicted LTV
