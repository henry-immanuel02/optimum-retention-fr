import streamlit as st
import hashlib
import pandas as pd
import plotly.graph_objects as go

# ================================
# Load dataset (pastikan file ada di folder yang sama dengan app.py)
# ================================
df = pd.read_parquet("Completed Net Loss Ratio by Risk Code dan TSI Range2.parquet")

# ================================
# User credentials (hash pakai blake2b.hexdigest())
# ================================
users = {
    "568622d8836e4856d75132f68bc2cdb16ee788ad6b72f74bc264f9757d8a54ded1c02cf2bb37b59420bc9f43dcd297b9a828d5f673d9a977b68b724650b1442a":
    "db1bc89118ae73eea00e2de5868a96cd25a80c3eb6cd62639a921ba5abfc1b6bee91783fc1a1167dc3e14966c56a23237eb635dfb4529f3ddbe533c9b8d609f4"
}

# ================================
# Mapping TSI RANGE → PML
# ================================
tsi_pml_map = {
    "01. [0, 500 Mio]": 5e8,
    "02. (500 Mio,  1 Bio]": 1e9,
    "03. (1 Bio, 5 Bio]": 5e9,
    "04. (5 Bio, 10 Bio]": 1e10,
    "05. (10 Bio, 25 Bio]": 2.5e10,
    "06. (25 Bio, 50 Bio]": 5e10,
    "07. (50 Bio, 75 Bio]": 7.5e10,
    "08. (75 Bio, 100 Bio]": 1e11,
    "09. (100 Bio, 250 Bio]": 2.5e11,
    "10. (250 Bio, 330 Bio]": 3.3e11,
    "11. (330 Bio, 500 Bio]": 5e11,
    "12. (500 Bio, 750 Bio]": 7.5e11,
    "13. (750 Bio, 1 T]": 1e12,
    "14. (1T, 2T]": 2e12,
    "15. (2 T, 3T]": 3e12,
    "16. > 3T": 5e12
}


# Helper format ke "Bio"
def format_bio(x):
    return f"{x/1e9:,.2f} Bio"

# ================================
# Header
# ================================
st.title("MNC Insurance Actuarial Dashboard")
st.markdown(
    """
    <p style='color:gray; font-size:14px;'>
    Aplikasi ini masih dalam tahap pengembangan. Bug, kritik, dan saran dapat disampaikan ke 
    <a href="mailto:henry.sihombing@mnc-insurance.com">henry.sihombing@mnc-insurance.com</a>
    </p>
    <hr style="border:1px solid #bbb; margin:20px 0;">
    """,
    unsafe_allow_html=True
)

# ================================
# Login system
# ================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    username_input = st.text_input("Masukkan Username")
    password_input = st.text_input("Masukkan Password", type="password")

    if st.button("Login"):
        username_hashed = hashlib.blake2b(username_input.encode("utf-8")).hexdigest()
        password_hashed = hashlib.blake2b(password_input.encode("utf-8")).hexdigest()

        if username_hashed in users and users[username_hashed] == password_hashed:
            st.session_state.logged_in = True
            st.success("Login berhasil!")
            st.rerun()
        else:
            st.error("❌ Username atau password salah")

# ================================
# Main App (setelah login)
# ================================
else:
    st.subheader("Optimum Share and CoR Calculator")

    # Dropdown Risk Code
    risk_selected = st.selectbox(
        "Pilih RISK CODE",
        options=df["RISK CODE"].unique()
    )

    # Dropdown TSI Range
    tsi_options = df[df["RISK CODE"] == risk_selected]["TSI RANGE"].unique()
    tsi_selected = st.selectbox(
        "Pilih TSI RANGE",
        options=tsi_options
    )

    # Ambil data row
    row = df[
        (df["RISK CODE"] == risk_selected) &
        (df["TSI RANGE"] == tsi_selected)
    ]

    if not row.empty:
        adj_net_lr = row["ADJ NET LR"].values[0]
        suggested_share = row["Suggested Share"].values[0]
        buffer_15 = row["Buffer 15%"].values[0]
        if suggested_share <= 0 and buffer15 <= 0:
            adj_net_lr = "-"

        # Dashboard metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Share to Retain", f"{suggested_share*100:.2f}%")
        col2.metric("Buffer 15%", f"{buffer_15*100:.2f}%")
        try:
            col3.metric("Net Loss Ratio", f"{adj_net_lr*100:.2f}%")
        except:
            col3.metric("Net Loss Ratio", f"-")

        # Exposure calculation berdasarkan TSI → PML
        pml = tsi_pml_map.get(tsi_selected, None)
        if pml is not None:
            retained_amount = suggested_share * pml
            buffer_amount = buffer_15 * pml

            st.write("### Retained in Amount")
            col_a, col_b = st.columns(2)
            col_a.metric("Retained Amount: ", format_bio(retained_amount))
            col_b.metric("Buffer 15%:", format_bio(buffer_amount))

        # Extra inputs
        if suggested_share > 0:
            komisi_ojk = st.number_input(
                "Masukkan Komisi OJK (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.2f"
            )
            ovr = st.number_input(
                "Masukkan OVR (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.2f"
            )

            if st.button("Calculate CoR"):
                cor = adj_net_lr*100 + komisi_ojk + ovr + 15

                if cor < 100:
                    st.success(f"📊 CoR = **{cor:.2f}%**")
                else:
                    st.markdown(
                        f"<span style='color:red; font-weight:bold;'>📊 CoR = {cor:.2f}%</span>",
                        unsafe_allow_html=True
                    )

                # Waterfall chart
                st.subheader("Expected UW Result")
                base = 100
                values = [-adj_net_lr*100, -komisi_ojk, -ovr, -15]
                labels = ["Gross Premium", "Net Loss Ratio", "Komisi OJK", "OVR", "OPEX", "Profit/Loss"]
                measures = ["absolute", "relative", "relative", "relative", "relative", "total"]

                final_val = base + sum(values)
                total_color = "green" if final_val > 0 else "red"

                fig = go.Figure(go.Waterfall(
                    name="CoR Breakdown",
                    orientation="v",
                    measure=measures,
                    x=labels,
                    text=[f"{base:.2f}%"] + [f"{v:.2f}%" for v in values] + [f"{final_val:.2f}%"],
                    y=[base] + values + [None],
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                    decreasing={"marker": {"color": "red"}},
                    increasing={"marker": {"color": "blue"}},
                    totals={"marker": {"color": total_color}}
                ))

                st.plotly_chart(fig, use_container_width=True)

        else:
            st.error("⚠️ This risk code is not recommended!")

    # Logout button
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
