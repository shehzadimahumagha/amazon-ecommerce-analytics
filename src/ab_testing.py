import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.power import TTestIndPower
from pathlib import Path

DEFAULT_COVARIATES = [
    "item_count", "avg_item_price", "payment_installments",
    "delivery_days", "cohort_index",
]


def construct_experiment(df, items_df):
    freight = (
        items_df.groupby("order_id")["freight_value"]
        .sum()
        .reset_index(name="total_freight")
    )
    out = df.merge(freight, on="order_id", how="left")
    out["total_freight"] = out["total_freight"].fillna(0)
    out["treatment"] = (out["total_freight"] == 0).astype(int)
    return out


def check_balance(experiment_df, covariates=None):
    if covariates is None:
        covariates = [c for c in DEFAULT_COVARIATES if c in experiment_df.columns]

    ctrl = experiment_df[experiment_df["treatment"] == 0]
    trt  = experiment_df[experiment_df["treatment"] == 1]

    rows = []
    for col in covariates:
        m0, m1 = ctrl[col].mean(), trt[col].mean()
        s0, s1 = ctrl[col].std(),  trt[col].std()
        pooled_std = np.sqrt((s0 ** 2 + s1 ** 2) / 2)
        smd = (m1 - m0) / pooled_std if pooled_std > 0 else 0.0
        rows.append({
            "covariate":       col,
            "mean_control":    round(m0, 4),
            "mean_treatment":  round(m1, 4),
            "smd":             round(smd, 4),
            "balanced":        abs(smd) <= 0.1,
        })

    return (
        pd.DataFrame(rows)
        .sort_values("smd", key=abs, ascending=False)
        .reset_index(drop=True)
    )


def run_ttest(experiment_df, outcome_col="revenue"):
    ctrl = experiment_df.loc[experiment_df["treatment"] == 0, outcome_col].dropna()
    trt  = experiment_df.loc[experiment_df["treatment"] == 1, outcome_col].dropna()

    t_stat, p_value = stats.ttest_ind(trt, ctrl, equal_var=False)

    lift = trt.mean() - ctrl.mean()
    pooled_std = np.sqrt((ctrl.std() ** 2 + trt.std() ** 2) / 2)
    cohens_d = lift / pooled_std if pooled_std > 0 else 0.0

    var_trt = trt.var() / len(trt)
    var_ctrl = ctrl.var() / len(ctrl)
    se = np.sqrt(var_trt + var_ctrl)
    df_welch = (var_trt + var_ctrl) ** 2 / (
        var_trt ** 2 / (len(trt) - 1) + var_ctrl ** 2 / (len(ctrl) - 1)
    )
    t_crit = stats.t.ppf(0.975, df=df_welch)

    return {
        "method":           "Welch t-test",
        "outcome":          outcome_col,
        "estimate":         lift,
        "lift_pct":         round(lift / ctrl.mean() * 100, 3),
        "ci_lower":         lift - t_crit * se,
        "ci_upper":         lift + t_crit * se,
        "p_value":          p_value,
        "t_stat":           t_stat,
        "cohens_d":         round(cohens_d, 4),
        "mean_control":     ctrl.mean(),
        "mean_treatment":   trt.mean(),
        "n_control":        len(ctrl),
        "n_treatment":      len(trt),
    }


def run_mann_whitney(experiment_df, outcome_col="revenue"):
    ctrl = experiment_df.loc[experiment_df["treatment"] == 0, outcome_col].dropna()
    trt  = experiment_df.loc[experiment_df["treatment"] == 1, outcome_col].dropna()

    u_stat, p_value = stats.mannwhitneyu(trt, ctrl, alternative="two-sided")
    rank_biserial_r = 1 - (2 * u_stat) / (len(trt) * len(ctrl))

    return {
        "method":             "Mann-Whitney U",
        "outcome":            outcome_col,
        "u_stat":             u_stat,
        "p_value":            p_value,
        "rank_biserial_r":    round(rank_biserial_r, 4),
        "median_control":     ctrl.median(),
        "median_treatment":   trt.median(),
        "n_control":          len(ctrl),
        "n_treatment":        len(trt),
    }


def regression_adjusted_ate(experiment_df, outcome_col="revenue", covariates=None):
    if covariates is None:
        covariates = [c for c in DEFAULT_COVARIATES if c in experiment_df.columns]

    formula = f"{outcome_col} ~ treatment + " + " + ".join(covariates)
    fit = smf.ols(
        formula,
        data=experiment_df.dropna(subset=[outcome_col] + covariates),
    ).fit(cov_type="HC3")

    ci = fit.conf_int().loc["treatment"]
    return {
        "method":    "OLS (HC3)",
        "outcome":   outcome_col,
        "estimate":  fit.params["treatment"],
        "se":        fit.bse["treatment"],
        "ci_lower":  ci.iloc[0],
        "ci_upper":  ci.iloc[1],
        "p_value":   fit.pvalues["treatment"],
        "r_squared": round(fit.rsquared, 4),
        "n_obs":     int(fit.nobs),
        "formula":   formula,
    }


def compute_sample_size(effect_size=0.2, alpha=0.05, power=0.8):
    n = TTestIndPower().solve_power(
        effect_size=effect_size, alpha=alpha, power=power, alternative="two-sided"
    )
    n_per_group = int(np.ceil(n))
    return {
        "effect_size":  effect_size,
        "alpha":        alpha,
        "power":        power,
        "n_per_group":  n_per_group,
        "total_n":      n_per_group * 2,
    }


def plot_ab_distributions(experiment_df, outcome_col="revenue", path=None):
    ctrl = experiment_df.loc[experiment_df["treatment"] == 0, outcome_col].dropna()
    trt  = experiment_df.loc[experiment_df["treatment"] == 1, outcome_col].dropna()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    log_ctrl = np.log1p(ctrl)
    log_trt  = np.log1p(trt)
    x = np.linspace(
        min(log_ctrl.min(), log_trt.min()),
        max(log_ctrl.max(), log_trt.max()),
        300,
    )
    for log_vals, color, label in [
        (log_ctrl, "#3498db", f"Control  (n={len(ctrl):,})"),
        (log_trt,  "#e74c3c", f"Treatment (n={len(trt):,})"),
    ]:
        kde = stats.gaussian_kde(log_vals)
        ax1.fill_between(x, kde(x), alpha=0.35, color=color)
        ax1.plot(x, kde(x), color=color, linewidth=1.8, label=label)
        ax1.axvline(log_vals.mean(), color=color, linestyle="--", linewidth=1, alpha=0.8)

    ax1.set_xlabel(f"log(1 + {outcome_col})", fontsize=11)
    ax1.set_ylabel("Density", fontsize=11)
    ax1.set_title("Distribution Comparison (log scale)", fontsize=12, fontweight="bold")
    ax1.legend(frameon=False, fontsize=9)
    ax1.grid(True, linestyle="--", alpha=0.4)

    bp = ax2.boxplot(
        [ctrl, trt],
        labels=["Control\n(paid freight)", "Treatment\n(free freight)"],
        patch_artist=True,
        showfliers=False,
        medianprops=dict(color="black", linewidth=2),
    )
    for box, color in zip(bp["boxes"], ["#3498db", "#e74c3c"]):
        box.set_facecolor(color)
        box.set_alpha(0.65)

    ax2.set_ylabel(f"{outcome_col} (R$)", fontsize=11)
    ax2.set_title(f"{outcome_col} by Group", fontsize=12, fontweight="bold")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x:,.0f}"))
    ax2.grid(True, axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    if path:
        plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.show()


def plot_confidence_intervals(results_list, path=None):
    plottable = [
        r for r in results_list
        if all(k in r for k in ("estimate", "ci_lower", "ci_upper"))
    ]
    if not plottable:
        raise ValueError("No results contain 'estimate', 'ci_lower', and 'ci_upper'.")

    palette = ["#3498db", "#2ecc71", "#e74c3c", "#9b59b6", "#f39c12"]

    fig, ax = plt.subplots(figsize=(9, max(3, len(plottable) * 1.4)))

    for i, result in enumerate(plottable):
        color = palette[i % len(palette)]
        est, lo, hi = result["estimate"], result["ci_lower"], result["ci_upper"]
        label = result.get("method", f"Method {i + 1}")

        ax.errorbar(
            est, i,
            xerr=[[est - lo], [hi - est]],
            fmt="o", color=color, capsize=6, capthick=1.5,
            markersize=8, linewidth=2,
        )
        p_str = f"p={result['p_value']:.4f}" if "p_value" in result else ""
        ax.text(
            hi + abs(hi - lo) * 0.04, i,
            f"  {p_str}", va="center", fontsize=9, color=color,
        )

    ax.axvline(0, color="black", linestyle="--", linewidth=1, alpha=0.55)
    ax.set_yticks(range(len(plottable)))
    ax.set_yticklabels(
        [r.get("method", f"Method {i + 1}") for i, r in enumerate(plottable)],
        fontsize=10,
    )
    ax.set_xlabel("Estimated Treatment Effect (R$)", fontsize=11)
    ax.set_title("Treatment Effect — Confidence Intervals", fontsize=12, fontweight="bold")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x:,.2f}"))
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    if path:
        plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.show()
