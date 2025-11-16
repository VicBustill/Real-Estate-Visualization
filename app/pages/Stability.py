# app/pages/Stability.py
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="Stability", page_icon="🧭", layout="wide")


def _load_csv_from_repo() -> pd.DataFrame:
    try:
        from utils.io import load_first_csv
    except Exception:
        import sys
        sys.path.append(str(Path(__file__).resolve().parents[1]))
        from utils.io import load_first_csv
    try:
        return load_first_csv("data")
    except Exception as e:
        st.error(f"Could not load CSV from data/: {e}")
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def prepare() -> pd.DataFrame:
    df = _load_csv_from_repo()
    if df.empty:
        return df
    for c in ("price", "squareFootage", "daysOnMarket"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "zipCode" in df:
        raw = df["zipCode"].astype(str)
        five = raw.str.extract(r"(\d{5})", expand=False)
        df["zipCode"] = five.fillna(raw).str.strip()
    if {"price", "squareFootage"}.issubset(df.columns):
        df["pps"] = np.where(df["squareFootage"] > 0,
                             df["price"]/df["squareFootage"], np.nan)
    return df


df = prepare()
if df.empty:
    st.warning("No data found.")
    st.stop()

st.title("🧭 Price Stability")

metric = st.radio(
    "Metric", ["Price", "Price per sqft", "Days on Market"], horizontal=True)
group_choice = st.radio("Group by", ["ZIP", "Bedrooms"], horizontal=True)

col_map = {"Price": "price", "Price per sqft": "pps",
           "Days on Market": "daysOnMarket"}
mcol = col_map[metric]
gcol = "zipCode" if group_choice == "ZIP" else "bedrooms"

if mcol not in df.columns or gcol not in df.columns:
    st.info(f"Need '{mcol}' and '{gcol}' in data.")
    st.stop()

# compute stability & CI


def stability_score(arr: np.ndarray) -> float:
    arr = arr[np.isfinite(arr)]
    if arr.size < 4:
        return np.nan
    med = np.median(arr)
    iqr = np.subtract(*np.percentile(arr, [75, 25]))
    return float(max(0.0, 1.0 - (iqr/med)) * 100.0) if med > 0 else np.nan


@st.cache_data(show_spinner=False)
def compute_table(df: pd.DataFrame, gcol: str, mcol: str) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(7)
    for g, sub in df[[gcol, mcol]].dropna().groupby(gcol):
        x = sub[mcol].to_numpy(dtype="float64")
        if x.size < 6:
            rows.append((g, np.median(x) if x.size else np.nan,
                        np.nan, np.nan, x.size, np.nan))
            continue
        # bootstrap CI
        B = min(400, 50 + x.size)  # quick & light
        stats = []
        for _ in range(B):
            bs = x[rng.integers(0, x.size, size=x.size)]
            stats.append(stability_score(bs))
        stats = np.array(stats, dtype="float64")
        ci_lo, ci_hi = float(np.nanpercentile(stats, 2.5)), float(
            np.nanpercentile(stats, 97.5))
        score = stability_score(x)
        outlier_share = float(np.mean((x < np.percentile(x, 25)-1.5*np.subtract(*np.percentile(x, [75, 25]))) |
                                      (x > np.percentile(x, 75)+1.5*np.subtract(*np.percentile(x, [75, 25])))))
        rows.append((g, float(np.median(x)), score,
                    outlier_share, x.size, (ci_lo, ci_hi)))
    tbl = pd.DataFrame(
        rows, columns=[gcol, "median", "stability", "outlier_share", "n", "ci"])
    return tbl.sort_values("stability", ascending=False)


tbl = compute_table(df, gcol, mcol)

# show chart with CI bands
chart_data = tbl.dropna(subset=["stability"]).copy()
chart_data["ci_lo"] = chart_data["ci"].apply(
    lambda t: t[0] if isinstance(t, tuple) else np.nan)
chart_data["ci_hi"] = chart_data["ci"].apply(
    lambda t: t[1] if isinstance(t, tuple) else np.nan)

base = alt.Chart(chart_data.reset_index(drop=True))
bars = base.mark_bar().encode(
    x=alt.X(f"{gcol}:N", title=group_choice, sort=None),
    y=alt.Y("stability:Q", title="Stability Score (0–100)"),
    tooltip=[alt.Tooltip("median", format=",.0f"), alt.Tooltip("stability", format=".1f"),
             alt.Tooltip("outlier_share", title="Outlier share", format=".1%"), alt.Tooltip("n", title="# comps")]
)
rules = base.mark_rule(color="#94a3b8").encode(
    x=f"{gcol}:N",
    y="ci_lo:Q",
    y2="ci_hi:Q"
)
st.altair_chart((bars + rules).properties(height=340),
                use_container_width=True)

# inspect a group
sel = st.selectbox(
    f"Inspect distribution for {group_choice}", chart_data[gcol].astype(str).tolist())
dist = df[df[gcol].astype(str) == str(sel)][mcol].dropna()
if not dist.empty:
    density = alt.Chart(pd.DataFrame({mcol: dist})).transform_density(
        mcol, as_=[mcol, "density"]
    ).mark_area(opacity=0.6).encode(x=alt.X(f"{mcol}:Q", title=metric), y="density:Q")
    st.altair_chart(density.properties(height=260), use_container_width=True)
st.caption("Stability = (1 − IQR/median)×100 with 95% bootstrap CI. Lower outlier share and higher stability indicate steadier pricing.")
