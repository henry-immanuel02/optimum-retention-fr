import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ---------------------------
# Load data
# ---------------------------
@st.cache_data
def load_data():
    return pd.read_parquet("Completed Net Loss Ratio by Risk Code dan TSI Range2.parquet")

df = load_data()

# ---------------------------
# Helper
# ---------------------------
def format_percent(x):
    return f"{x*100:.2f}%"

def format_bio(x):
    return f"{x/1e9:,.2f} Bio"

# Mapping TSI RANGE ke PML
tsi_pml_map = {
    "01. [0, 500 Mio]": 5e8,
    "02. (500 Mio, 1 Bio]": 1e9,
    "03. (1 Bio, 5 Bio]": 5e9,
    "04. (5 Bio, 10 Bio]": 1e10,
    "05. (10 Bio, 25 Bio]": 2.5e10,
    "06. (25 Bio, 50 Bio]": 5e10,
    "07. (50 Bio, 75 Bio]": 7.5e10,
    "08. (75 Bio, 100 Bio]": 1e11,
    "09. (100 Bio, 250 Bio]": 2.5e11,
    "10. (250 Bio, 500 Bio]": 5e11,
    "11. (500 Bio, 750 Bio]": 7.5e11,
    "12. (750 Bio, 1 T]": 1e12,
    "13. (1T, 2T]": 2e12,
    "14. (2T, 3T]": 3e12,
    "15. > 3T": 5e12
}

def get_pml(tsi_selected):
    # cari key yang terkandung di string
    for key in tsi_pml_map:
        if key in tsi_selected:
            return tsi_pml_map[key]
    return None

# ---------------------------
# Sidebar
# ---------------------------
st.sidebar.header("Filter")
risk_selected = st.sidebar.selectbox("Pilih Risk Code", df["RISK_CODE"].unique())
tsi_selected = st.sidebar.selectbox("Pilih TSI Range", df["TSI_RANGE"].unique())

# Filter dataset
filtered_df = df[(df["RISK_CODE"] == risk_selected) & (df["TSI_RANGE"] == tsi_selected)]

# ---------------------------
# Main
# ---------------------------
st.title("📊 Actuarial Dashboard")

if not filtered_df.empty:
    net_lr = filtered_df["NET_LR"].values[0]
    suggested_share = max(0, min(1, 0.75 - net_lr))  # contoh formula
    buffer_15 = suggested_share * 1.15

    # Metrics utama
    col1, col2 = st.columns(2)
    col1.metric("Share to Retain", format_percent(suggested_share))
    col2.metric("Buffer 15%", format_percent(buffer_15))

    # Ambil PML
    pml = get_pml(tsi_selected)
    if pml is not None:
        retained_amount = suggested_share * pml
        buffer_amount = buffer_15 * pml

        st.write("### Retained Exposure")
        col_a, col_b = st.columns(2)
        col_a.metric("Retained (Share × PML)", format_bio(retained_amount))
        col_b.metric("Buffer (15% × PML)", format_bio(buffer_amount))
    else:
        st.warning(f"Tidak ditemukan PML untuk '{tsi_selected}'")

    # Chart distribusi NET_LR (opsional)
    st.write("### Distribusi Net Loss Ratio")
    fig = px.histogram(df, x="NET_LR", nbins=30, title="Net Loss Ratio Distribution")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Data tidak ditemukan untuk filter tersebut.")
