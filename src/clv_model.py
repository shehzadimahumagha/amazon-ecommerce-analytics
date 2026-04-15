import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data
from pathlib import Path

TIER_COLORS = {
    "Bronze":   "#cd7f32",
    "Silver":   "#a8a9ad",
    "Gold":     "#ffd700",
    "Platinum": "#8a9ba8",
}
TIER_ORDER = ["Bronze", "Silver", "Gold", "Platinum"]


def compute_historical_clv(df):
    cutoff = df["order_purchase_timestamp"].max() - pd.DateOffset(months=12)
    recent = df[df["order_purchase_timestamp"] >= cutoff]

    clv = (
        recent.groupby("customer_unique_id")
        .agg(
            historical_clv=("revenue", "sum"),
            order_count=("order_id", "count"),
            avg_order_value=("revenue", "mean"),
            first_purchase=("order_purchase_timestamp", "min"),
            last_purchase=("order_purchase_timestamp", "max"),
        )
        .reset_index()
    )
    clv["tier"] = pd.qcut(
        clv["historical_clv"],
        q=4,
        labels=TIER_ORDER,
        duplicates="drop",
    )
    return clv


def build_rfm_summary_lifetimes(df, observation_period_end=None):
    if observation_period_end is None:
        observation_period_end = df["order_purchase_timestamp"].max()

    summary = summary_data_from_transaction_data(
        df,
        customer_id_col="customer_unique_id",
        datetime_col="order_purchase_timestamp",
        monetary_value_col="revenue",
        observation_period_end=observation_period_end,
        freq="W",
    )
    return summary


def compute_probabilistic_clv(df, months=12, observation_period_end=None):
    summary = build_rfm_summary_lifetimes(df, observation_period_end)

    bgf = BetaGeoFitter(penalizer_coef=0.01)
    bgf.fit(summary["frequency"], summary["recency"], summary["T"])

    repeat_buyers = summary[summary["frequency"] > 0]
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(repeat_buyers["frequency"], repeat_buyers["monetary_value"])

    predicted_clv = ggf.customer_lifetime_value(
        bgf,
        summary["frequency"],
        summary["recency"],
        summary["T"],
        summary["monetary_value"],
        time=months,
        freq="W",
        discount_rate=0.01,
    )

    result = summary.copy()
    result["predicted_clv"] = predicted_clv
    result["tier"] = pd.qcut(
        result["predicted_clv"],
        q=4,
        labels=TIER_ORDER,
        duplicates="drop",
    )
    result = result.reset_index()
    return result, bgf, ggf


def plot_clv_distribution(clv_df, clv_col="historical_clv", path=None):
    valid_tiers = [t for t in TIER_ORDER if t in clv_df["tier"].cat.categories]
    tier_stats = (
        clv_df.groupby("tier", observed=True)[clv_col]
        .agg(["sum", "mean", "count"])
        .reindex(valid_tiers)
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    values = clv_df[clv_col].dropna()
    ax1.hist(np.log1p(values), bins=60, color="#3498db", alpha=0.85, edgecolor="none")
    ax1.set_xlabel("log(1 + CLV)  [R$]", fontsize=11)
    ax1.set_ylabel("Customer Count", fontsize=11)
    ax1.set_title("CLV Distribution (log scale)", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.4)

    colors = [TIER_COLORS[t] for t in tier_stats.index]
    bars = ax2.bar(tier_stats.index, tier_stats["sum"], color=colors, edgecolor="none", alpha=0.92)
    for bar, (_, row) in zip(bars, tier_stats.iterrows()):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 1.01,
            f"n={int(row['count']):,}",
            ha="center", va="bottom", fontsize=9,
        )
    ax2.set_ylabel("Total Revenue (R$)", fontsize=11)
    ax2.set_title("Total Revenue by CLV Tier", fontsize=12, fontweight="bold")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x:,.0f}"))
    ax2.grid(True, axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    if path:
        plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.show()


def plot_clv_by_category(df, clv_df, clv_col="historical_clv", top_n=20, path=None):
    first_cat = (
        df.sort_values("order_purchase_timestamp")
        .groupby("customer_unique_id")["product_category"]
        .first()
        .reset_index()
        .rename(columns={"product_category": "first_category"})
    )

    merged = clv_df.merge(first_cat, on="customer_unique_id", how="left")
    cat_clv = (
        merged.groupby("first_category")[clv_col]
        .median()
        .dropna()
        .sort_values(ascending=False)
        .head(top_n)
    )

    gradient = plt.cm.RdYlGn(np.linspace(0.15, 0.85, len(cat_clv)))

    fig, ax = plt.subplots(figsize=(11, max(5, len(cat_clv) * 0.42)))
    ax.barh(
        cat_clv.index[::-1],
        cat_clv.values[::-1],
        color=gradient,
        edgecolor="none",
        height=0.7,
    )
    ax.set_xlabel("Median CLV (R$)", fontsize=12)
    ax.set_title(
        f"Median CLV by First Purchase Category (Top {top_n})",
        fontsize=13,
        fontweight="bold",
    )
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x:,.0f}"))
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()

    if path:
        plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.show()
