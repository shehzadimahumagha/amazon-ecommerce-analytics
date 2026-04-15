import pandas as pd
import numpy as np
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

CSV_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

DATE_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def load_olist_data(data_dir):
    data_dir = Path(data_dir)
    return {name: pd.read_csv(data_dir / fname) for name, fname in CSV_FILES.items()}


def build_master_table(dfs):
    payments = (
        dfs["order_payments"]
        .groupby("order_id")
        .agg(
            payment_value=("payment_value", "sum"),
            payment_installments=("payment_installments", "max"),
        )
        .reset_index()
    )

    reviews = (
        dfs["order_reviews"]
        .sort_values("review_answer_timestamp")
        .drop_duplicates("order_id", keep="last")[["order_id", "review_score"]]
    )

    products = dfs["products"].merge(
        dfs["category_translation"], on="product_category_name", how="left"
    )

    df = (
        dfs["orders"]
        .merge(dfs["customers"], on="customer_id", how="left")
        .merge(dfs["order_items"], on="order_id", how="left")
        .merge(
            products[["product_id", "product_category_name_english"]],
            on="product_id",
            how="left",
        )
        .merge(dfs["sellers"][["seller_id", "seller_state"]], on="seller_id", how="left")
        .merge(payments, on="order_id", how="left")
        .merge(reviews, on="order_id", how="left")
    )
    return df


def cast_dtypes(df):
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df


def clean_master_table(df):
    df = df[df["order_status"] == "delivered"].copy()
    df = df[(df["payment_value"] > 0) & (df["price"] > 0)]
    df = df.dropna(subset=["order_purchase_timestamp", "customer_unique_id"])
    return df.reset_index(drop=True)


def add_time_features(df):
    df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M")
    df["cohort_month"] = (
        df.groupby("customer_unique_id")["order_purchase_timestamp"]
        .transform("min")
        .dt.to_period("M")
    )
    df["cohort_index"] = (df["order_month"] - df["cohort_month"]).apply(lambda x: x.n)
    df["order_year"] = df["order_purchase_timestamp"].dt.year
    df["order_dow"] = df["order_purchase_timestamp"].dt.dayofweek
    df["order_hour"] = df["order_purchase_timestamp"].dt.hour
    df["delivery_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.days
    return df


def add_order_level_features(df):
    def modal_category(x):
        valid = x.dropna()
        return valid.mode().iloc[0] if not valid.empty else np.nan

    return (
        df.groupby("order_id")
        .agg(
            customer_unique_id=("customer_unique_id", "first"),
            customer_state=("customer_state", "first"),
            seller_state=("seller_state", "first"),
            order_purchase_timestamp=("order_purchase_timestamp", "first"),
            order_month=("order_month", "first"),
            cohort_month=("cohort_month", "first"),
            cohort_index=("cohort_index", "first"),
            order_year=("order_year", "first"),
            order_dow=("order_dow", "first"),
            order_hour=("order_hour", "first"),
            delivery_days=("delivery_days", "first"),
            revenue=("payment_value", "first"),
            payment_installments=("payment_installments", "first"),
            item_count=("order_item_id", "max"),
            avg_item_price=("price", "mean"),
            review_score=("review_score", "first"),
            product_category=("product_category_name_english", modal_category),
        )
        .reset_index()
    )


def validate_data(df):
    assert df["order_id"].is_unique, "order_id not unique after aggregation"
    assert df["revenue"].gt(0).all(), "non-positive revenue values found"
    assert df["cohort_index"].ge(0).all(), "negative cohort index found"
    assert df["order_purchase_timestamp"].notna().all(), "null purchase timestamps"
    assert df["item_count"].ge(1).all(), "item_count below 1"
    return df


def save_processed(df, path=None, out_dir=None):
    if path is None:
        out_dir = Path(out_dir) if out_dir is not None else PROCESSED_DIR
        path = out_dir / "master_clean.parquet"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = df.copy()
    for col in df.columns:
        if isinstance(df[col].dtype, pd.PeriodDtype):
            df[col] = df[col].astype(str)
    df.to_parquet(path, index=False)
    print(f"saved -> {path}")
    return path


def load_processed(path):
    return pd.read_parquet(path)


def run_pipeline(data_dir, output_path):
    dfs = load_olist_data(data_dir)
    df = build_master_table(dfs)
    df = cast_dtypes(df)
    df = clean_master_table(df)
    df = add_time_features(df)
    df = add_order_level_features(df)
    df = validate_data(df)
    save_processed(df, output_path)
    return df
