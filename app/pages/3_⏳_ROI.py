# app/pages/ROI.py
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from utils.style import apply_theme

st.set_page_config(page_title="ROI", page_icon="⏳", layout="wide")
apply_theme()

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
    df["price"] = pd.to_numeric(df.get("price"), errors="coerce")
    for c in ("listedDate", "createdDate", "lastSeenDate"):
        if c in df:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    if "zipCode" in df:
        raw = df["zipCode"].astype(str)
        five = raw.str.extract(r"(\d{5})", expand=False)
        df["zipCode"] = five.fillna(raw).str.strip()
    return df


def _pick_date_col(df: pd.DataFrame) -> str | None:
    for c in ("listedDate", "createdDate", "lastSeenDate"):
        if c in df and pd.api.types.is_datetime64_any_dtype(df[c]):
            return c
    return None


def _empirical_returns(df: pd.DataFrame) -> tuple[float, float, dict]:
    """
    Compute annual log-return mean & std from median yearly prices.
    Returns (mu, sigma, per_zip_mu_sigma).
    """
    date_col = _pick_date_col(df)
    if date_col is None or "price" not in df:
        return 0.03, 0.12, {}  # default if no dates

    d = df[[date_col, "price", "zipCode"]].dropna().copy()
    d["year"] = d[date_col].dt.year
    if d.empty:
        return 0.03, 0.12, {}

    yearly = d.groupby(["zipCode", "year"])["price"].median().reset_index()
    # log returns by zip
    per_zip = {}
    for z, g in yearly.groupby("zipCode"):
        g = g.sort_values("year")
        if len(g) >= 3:
            r = np.diff(np.log(g["price"].to_numpy()))
            if np.isfinite(r).any():
                per_zip[z] = (float(np.mean(r)), float(
                    np.std(r, ddof=1) if len(r) > 1 else 0.10))
    # global fallback
    all_years = yearly.groupby("year")["price"].median().sort_index()
    if len(all_years) >= 3:
        r_all = np.diff(np.log(all_years.to_numpy()))
        mu_g = float(np.mean(r_all))
        sig_g = float(np.std(r_all, ddof=1))
    else:
        mu_g, sig_g = 0.03, 0.12

    return mu_g, sig_g, per_zip


df = prepare()
if df.empty or "price" not in df.columns:
    st.warning("Need prices in /data.")
    st.stop()

st.title("⏳ Projected Gain / Depreciation")

mode = st.radio("Mode", ["Deterministic", "Monte Carlo"], horizontal=True)
c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
with c1:
    horizon = st.select_slider("Horizon (years)", options=[
                               1, 5, 10, 25, 50], value=10)
with c2:
    hold_rate = st.number_input(
        "Annual holding cost %", value=0.0, min_value=0.0, max_value=20.0, step=0.1)
with c3:
    thresh = st.number_input("Profit threshold ($)", value=0.0, step=1000.0)
with c4:
    by_zip = st.checkbox("Summaries by ZIP", value=True)

mu_g, sig_g, per_zip = _empirical_returns(df)

if mode == "Deterministic":
    g = st.number_input("Annual growth assumption %",
                        value=round(mu_g*100, 1), step=0.1) / 100.0
    r = hold_rate / 100.0
    years = float(horizon)
    prices = df["price"].astype("float64").to_numpy()

    fv = prices * np.power(1.0 + g, years)
    geom_sum = years if g == 0 else (np.power(1.0 + g, years) - 1.0) / g
    hold = prices * r * geom_sum
    net = fv - prices - hold

    out = df.copy()
    out["net_gain"] = net
    out["proj_value"] = fv

    st.metric("Median net gain", f"${np.nanmedian(net):,.0f}")
    st.metric("Share profitable", f"{(net>thresh).mean()*100:.1f}%")

    if by_zip and "zipCode" in out:
        agg = (out.groupby("zipCode")["net_gain"].median()
               .reset_index(name="median_net_gain").sort_values("median_net_gain", ascending=False).head(25))
        chart = alt.Chart(agg).mark_bar().encode(
            x=alt.X("zipCode:N", title="ZIP", sort=None),
            y=alt.Y("median_net_gain:Q",
                    title=f"Median net gain over {int(years)}y ($)"),
            tooltip=[alt.Tooltip("median_net_gain", format=",.0f")]
        ).properties(height=360).interactive()
        st.altair_chart(chart, use_container_width=True)

    with st.expander("Rows with projections", expanded=False):
        cols = [c for c in ("formattedAddress", "zipCode", "bedrooms",
                            "price", "proj_value", "net_gain") if c in out.columns]
        st.dataframe(out[cols].sort_values(
            "net_gain", ascending=False).head(400), use_container_width=True)

else:  # Monte Carlo
    sims = int(st.slider("Simulations", 200, 4000, 1500, 100))
    # allow user to tweak mean/vol (defaults from data)
    mu_user = st.number_input(
        "Mean annual log-return μ (%)", value=round(mu_g*100, 2), step=0.05)/100.0
    sig_user = st.number_input(
        "Volatility σ (%)", value=round(sig_g*100, 2), step=0.05)/100.0
    use_zip_params = st.checkbox("Use per-ZIP μ,σ when available", value=True)

    prices = df["price"].astype("float64").to_numpy()
    r = hold_rate / 100.0
    Y = int(horizon)

    # choose mu,sigma per row
    if use_zip_params and "zipCode" in df and per_zip:
        mu = df["zipCode"].map(lambda z: per_zip.get(str(z), (mu_user, sig_user))[
                               0]).astype("float64").to_numpy()
        sg = df["zipCode"].map(lambda z: per_zip.get(str(z), (mu_user, sig_user))[
                               1]).astype("float64").to_numpy()
    else:
        mu = np.full(len(prices), mu_user, dtype="float64")
        sg = np.full(len(prices), sig_user, dtype="float64")

    # simulate terminal values (vectorized per listing)
    rng = np.random.default_rng(42)
    # log-returns per year summed over horizon ~ Normal(Y*mu, Y*sg^2)
    mu_T = mu*Y
    sg_T = sg*np.sqrt(Y)
    z = rng.normal(loc=0.0, scale=1.0, size=(sims, len(prices)))
    # terminal gross multiplier
    mult = np.exp(mu_T + sg_T*z)
    fv = prices * mult
    # holding cost (geometric)
    geom_sum = np.where(mu != 0, (np.exp(mu*Y) - 1.0)/mu, Y)
    hold = prices * r * geom_sum
    net = fv - prices - hold
    # portfolio distribution across listings (median per sim)
    port_net = np.nanmedian(net, axis=1)

    prob_profit = float((port_net > thresh).mean())
    var5 = float(np.quantile(port_net, 0.05))
    mean_net = float(np.mean(port_net))

    k1, k2, k3 = st.columns(3)
    k1.metric("P(net gain > threshold)", f"{prob_profit*100:.1f}%")
    k2.metric("Portfolio VaR (5%)", f"${var5:,.0f}")
    k3.metric("Expected net gain", f"${mean_net:,.0f}")

    # distribution chart
    dist = pd.DataFrame({"net_gain": port_net})
    chart = (alt.Chart(dist).transform_density(
        "net_gain", as_=["net_gain", "density"], extent=[float(dist["net_gain"].min()), float(dist["net_gain"].max())]
    ).mark_area(opacity=0.6).encode(
        x=alt.X("net_gain:Q",
                title=f"Portfolio median net gain over {Y}y ($)"),
        y="density:Q"
    ).properties(height=320))
    st.altair_chart(chart, use_container_width=True)
    st.caption("Monte Carlo assumes log‑normal annual returns; μ, σ estimated from your data when dates exist, else user inputs.")
