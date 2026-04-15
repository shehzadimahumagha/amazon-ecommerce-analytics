import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import squarify
from pathlib import Path

SEGMENT_COLORS = {
    "Champions":          "#2ecc71",
    "Loyal Customers":    "#27ae60",
    "Potential Loyalists":"#3498db",
    "Promising":          "#1abc9c",
    "Can't Lose Them":    "#e67e22",
    "At Risk":            "#e74c3c",
    "Hibernating":        "#95a5a6",
    "Lost":               "#7f8c8d",
}


def assign_segment(r, f, m):
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r <= 2 and f >= 4:
        return "Can't Lose Them"
    if r >= 3 and f >= 3:
        return "Loyal Customers"
    if r >= 4:
        return "Potential Loyalists"
    if r == 3:
        return "Promising"
    if f >= 3:
        return "At Risk"
    if r == 2:
        return "Hibernating"
    return "Lost"


def compute_rfm(df, snapshot_date=None):
    if snapshot_date is None:
        snapshot_date = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)

    rfm = (
        df.groupby("customer_unique_id")
        .agg(
            last_purchase=("order_purchase_timestamp", "max"),
            frequency=("order_id", "count"),
            monetary=("revenue", "sum"),
        )
        .reset_index()
    )
    rfm["recency"] = (snapshot_date - rfm["last_purchase"]).dt.days

    rfm["r_score"] = pd.qcut(
        rfm["recency"].rank(method="first"), q=5, labels=[5, 4, 3, 2, 1]
    ).astype(int)
    rfm["f_score"] = pd.qcut(
        rfm["frequency"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]
    ).astype(int)
    rfm["m_score"] = pd.qcut(
        rfm["monetary"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]
    ).astype(int)

    rfm["segment"] = rfm.apply(
        lambda row: assign_segment(row["r_score"], row["f_score"], row["m_score"]), axis=1
    )
    return rfm


def segment_summary(rfm):
    total_customers = len(rfm)
    total_revenue = rfm["monetary"].sum()

    summary = (
        rfm.groupby("segment")
        .agg(
            customer_count=("customer_unique_id", "count"),
            avg_recency=("recency", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            total_revenue=("monetary", "sum"),
            avg_r_score=("r_score", "mean"),
            avg_f_score=("f_score", "mean"),
            avg_m_score=("m_score", "mean"),
        )
        .reset_index()
    )
    summary["pct_customers"] = (summary["customer_count"] / total_customers * 100).round(1)
    summary["pct_revenue"] = (summary["total_revenue"] / total_revenue * 100).round(1)
    return summary.sort_values("customer_count", ascending=False).reset_index(drop=True)


def plot_rfm_treemap(rfm, path=None):
    summary = segment_summary(rfm)
    sizes = summary["customer_count"].values
    labels = [
        f"{row['segment']}\n{row['customer_count']:,} ({row['pct_customers']}%)"
        for _, row in summary.iterrows()
    ]
    colors = [SEGMENT_COLORS.get(seg, "#bdc3c7") for seg in summary["segment"]]

    fig, ax = plt.subplots(figsize=(14, 8))
    squarify.plot(
        sizes=sizes,
        label=labels,
        color=colors,
        alpha=0.85,
        ax=ax,
        text_kwargs={"fontsize": 10, "fontweight": "bold"},
    )
    ax.axis("off")
    ax.set_title("Customer Segments — RFM Treemap", fontsize=14, fontweight="bold", pad=12)
    plt.tight_layout()

    if path:
        plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.show()


def plot_rfm_scatter(rfm, path=None):
    m_norm = (rfm["monetary"] - rfm["monetary"].min()) / (
        rfm["monetary"].max() - rfm["monetary"].min()
    )
    sizes = 20 + m_norm * 200

    fig, ax = plt.subplots(figsize=(10, 7))
    for segment, group in rfm.groupby("segment"):
        ax.scatter(
            group["r_score"],
            group["f_score"],
            c=SEGMENT_COLORS.get(segment, "#bdc3c7"),
            s=sizes.loc[group.index],
            label=segment,
            alpha=0.55,
            edgecolors="none",
        )

    ax.set_xlabel("Recency Score", fontsize=12)
    ax.set_ylabel("Frequency Score", fontsize=12)
    ax.set_title(
        "RFM Scatter — Recency vs Frequency  (point size = Monetary)",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", frameon=False, fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    if path:
        plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.show()


def plot_monetary_distribution(rfm, path=None):
    order = (
        rfm.groupby("segment")["monetary"]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )
    data = [rfm.loc[rfm["segment"] == seg, "monetary"].values for seg in order]
    colors = [SEGMENT_COLORS.get(seg, "#bdc3c7") for seg in order]

    fig, ax = plt.subplots(figsize=(12, 6))
    bp = ax.boxplot(data, patch_artist=True, notch=False, showfliers=False)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)

    ax.set_xticks(range(1, len(order) + 1))
    ax.set_xticklabels(order, rotation=30, ha="right", fontsize=10)
    ax.set_ylabel("Revenue (R$)", fontsize=12)
    ax.set_title("Revenue Distribution by Customer Segment", fontsize=13, fontweight="bold")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()

    if path:
        plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.show()
