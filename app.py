from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="The Economics of Digital Payment Fraud in India",
    page_icon="🔎",
    layout="wide",
)

BASE = Path(__file__).resolve().parent
FILE_CANDIDATES = {
    "rbi": ["01_raw_data.XLSX", "01_raw_data.xlsx", "Domestic_Fraud_Raw.xlsx"],
    "upi": ["UPI_monthly_stats.xlsx"],
    "transactions": ["transactions.csv", "transactions(1).csv"],
    "labels": ["fraud_labels.csv", "fraud_labels(1).csv"],
}


def locate_file(key):
    for name in FILE_CANDIDATES[key]:
        path = BASE / name
        if path.exists():
            return path
    return None


def read_rbi(path):
    if path is None:
        return None
    xls = pd.ExcelFile(path)
    # Sheet1 is the curated 30-month series; the other sheet is the wider source extract.
    sheet = "Sheet1" if "Sheet1" in xls.sheet_names else xls.sheet_names[0]
    raw = pd.read_excel(path, sheet_name=sheet).dropna(how="all").iloc[:, :5].copy()
    raw.columns = ["month", "fraud_volume_lakh", "amount_involved_crore", "one_in_x_transactions", "fts_bps"]
    raw["month"] = raw["month"].astype(str).str.strip().replace({"Jauuary 2025": "January 2025"})
    raw["month"] = pd.to_datetime(raw["month"], format="%B %Y", errors="raise")
    for col in ["fraud_volume_lakh", "amount_involved_crore", "one_in_x_transactions"]:
        raw[col] = pd.to_numeric(raw[col], errors="raise")
    raw["fts_bps"] = pd.to_numeric(
        raw["fts_bps"].astype(str).str.replace("bps", "", regex=False).str.strip(), errors="raise"
    )
    return raw.sort_values("month").reset_index(drop=True)


def read_upi(path):
    if path is None:
        return None
    required = [
        "Month", "Volume (In Mn.)", "Avg. Daily Volume (In Mn.)", "Value (In Cr.)",
        "Avg. Daily Value (In Cr.)", "Banks live on UPI",
    ]
    df = pd.read_excel(path, sheet_name=0)
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"UPI workbook missing columns: {missing}")
    df = df[required].copy()
    df["Month"] = pd.to_datetime(df["Month"], errors="raise")
    for col in required[1:]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    df = df.sort_values("Month").reset_index(drop=True)
    # ₹ crore / million transactions × 10 converts to rupees per transaction.
    df["avg_transaction_value_rupees"] = df["Value (In Cr.)"] / df["Volume (In Mn.)"] * 10
    return df


@st.cache_data(show_spinner=False)
def load_data(rbi_path, upi_path, tx_path, label_path):
    rbi = read_rbi(Path(rbi_path) if rbi_path else None)
    upi = read_upi(Path(upi_path) if upi_path else None)
    tx = pd.read_csv(tx_path) if tx_path else None
    labels = pd.read_csv(label_path) if label_path else None
    return rbi, upi, tx, labels


paths = {key: locate_file(key) for key in FILE_CANDIDATES}
try:
    rbi, upi, tx, labels = load_data(
        str(paths["rbi"]) if paths["rbi"] else None,
        str(paths["upi"]) if paths["upi"] else None,
        str(paths["transactions"]) if paths["transactions"] else None,
        str(paths["labels"]) if paths["labels"] else None,
    )
    load_error = None
except Exception as exc:
    rbi = upi = tx = labels = None
    load_error = str(exc)

recon = None
if tx is not None and labels is not None and {"transaction_id", "is_fraud"}.issubset(tx.columns) and {"transaction_id", "is_fraud"}.issubset(labels.columns):
    recon = tx[["transaction_id", "is_fraud"]].merge(
        labels[["transaction_id", "is_fraud"]], on="transaction_id", how="outer",
        suffixes=("_transaction", "_label"), indicator=True,
    )
    recon["label_match"] = recon["is_fraud_transaction"].eq(recon["is_fraud_label"]) & recon["_merge"].eq("both")

# ---------- Page header and navigation: clear title, purpose and authorship ----------
st.title("The Economics of Digital Payment Fraud in India")
st.markdown(
    """
    <div style="display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;margin-top:-4px;margin-bottom:18px;">
      <div style="display:flex;align-items:center;gap:9px;flex-wrap:wrap;">
        <span style="display:inline-block;padding:7px 11px;border-radius:7px;background:#172d43;border:1px solid #315675;color:#a9d7ff;font-size:.91rem;font-weight:700;">Exploratory Market Assessment</span>
        <span style="color:#aeb9c7;font-size:.92rem;">A point of view, not a verdict</span>
        <span style="color:#667487;">•</span>
        <span style="color:#aeb9c7;font-size:.92rem;">No production fraud scoring</span>
      </div>
      <div style="text-align:right;color:#c9d8e8;font-size:.9rem;line-height:1.5;">
        <span style="color:#8ebeff;">Prepared by</span> <strong style="color:#f3f7fc;">Harshana</strong><br>
        MBA Finance, IMT Ghaziabad <span style="color:#718096;">·</span> <strong style="color:#c9d8e8;">Independent Portfolio Research</strong>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

start_tab, market_tab, synthetic_tab, economics_tab, competition_tab, decision_tab = st.tabs([
    "Start Here", "Fraud & UPI Trends", "Synthetic Data", "Buyer Economics", "Existing Solutions", "Recommendation & Evidence"
])

with start_tab:
    st.markdown("### The Big Question")
    intro_left, intro_right = st.columns([1.08, 1], gap="medium")
    with intro_left:
        st.markdown("**Digital payments are growing fast. But where might banks still be struggling with fraud, and is that problem worth paying to solve?**")
        st.write("This started with curiosity, not a product pitch. I wanted to understand what the available evidence could tell us, where it stopped being useful, and whether there might be a real business problem worth exploring.")
        st.write("This is a desk-based exploration using public research, data checks and a what-if model. It is a starting point, not a verdict. The goal was **not to prove a market gap**, but to work out what is worth investigating next.")
    with intro_right:
        st.markdown("""
        <div style="background:linear-gradient(145deg,#17324a 0%,#17283a 100%);border:1px solid #3d6d91;border-radius:14px;padding:20px 22px;height:100%;box-shadow:0 8px 24px rgba(0,0,0,.16);">
          <div style="font-size:0.82rem;letter-spacing:.09em;text-transform:uppercase;color:#80c5ff;font-weight:800;">My Point Of View</div>
          <div style="font-size:1.2rem;line-height:1.4;font-weight:750;margin-top:10px;color:#f5f8fc;">Don't rush to build another fraud-detection tool.</div>
          <div style="font-size:0.95rem;line-height:1.55;margin-top:9px;color:#d8e7f4;">Established platforms already offer many detection capabilities. A narrower problem in post-complaint work, like finding evidence and preparing responses, may be worth testing with banks.</div>
          <div style="display:flex;align-items:center;gap:9px;margin-top:16px;padding-top:14px;border-top:1px solid #35536b;">
            <span style="background:#173a2b;color:#a9f0ca;padding:5px 9px;border-radius:6px;font-size:.78rem;font-weight:800;letter-spacing:.04em;">NEXT STEP</span>
            <span style="color:#f5f8fc;font-weight:700;line-height:1.4;">Validate the workflow pain before recommending a launch.</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("### The Research Journey")
    st.markdown("""
    <div style="display:flex;align-items:flex-start;gap:12px;padding:13px 16px;margin:0 0 14px;border-radius:10px;background:linear-gradient(90deg,#172d43 0%,#151d28 100%);border-left:4px solid #58a6ff;">
      <div style="font-size:1.05rem;line-height:1.5;color:#eaf4ff;font-weight:650;">Why this page exists</div>
      <div style="font-size:1.02rem;line-height:1.5;color:#cbd9e8;">To show how a broad question became a specific, testable business hypothesis.</div>
    </div>
    """, unsafe_allow_html=True)
    journey = [
        ("01", "Get the Context", "RBI data for reported fraud. NPCI data for UPI growth. Two different lenses, not one fraud-rate calculation.", "#2E86DE"),
        ("02", "Check the Data", "Clean dates and numbers, check gaps and duplicates, and reconcile transaction IDs and labels.", "#17A589"),
        ("03", "Look at what exists", "Review commercial fraud platforms and public or shared-intelligence initiatives before assuming the market needs another tool.", "#9B59B6"),
        ("04", "Test the Business Case", "Model a narrower workflow idea with editable assumptions, then list what real buyers would need to confirm.", "#E67E22"),
    ]
    journey_cols = st.columns(4)
    for col, (num, heading, body, accent) in zip(journey_cols, journey):
        with col:
            st.markdown(f"""
            <div style="height:100%;min-height:205px;padding:18px;border:1px solid #343b46;border-radius:14px;background:linear-gradient(180deg,{accent}20 0%,rgba(20,24,31,.35) 70%);">
              <div style="font-size:1.9rem;font-weight:800;color:{accent};">{num}</div>
              <div style="font-size:1.02rem;font-weight:750;margin:10px 0 8px;color:#f4f6f8;">{heading}</div>
              <div style="font-size:.91rem;line-height:1.55;color:#cbd3dd;">{body}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:18px 0 8px;">
      <span style="padding:8px 12px;border-radius:8px;background:#1d2937;color:#e8f2fc;font-weight:650;">Broad Question</span>
      <span style="color:#80c5ff;font-size:1.2rem;">→</span>
      <span style="padding:8px 12px;border-radius:8px;background:#1d2937;color:#e8f2fc;font-weight:650;">Evidence Checks</span>
      <span style="color:#80c5ff;font-size:1.2rem;">→</span>
      <span style="padding:8px 12px;border-radius:8px;background:#1d2937;color:#e8f2fc;font-weight:650;">Existing Alternatives</span>
      <span style="color:#80c5ff;font-size:1.2rem;">→</span>
      <span style="padding:8px 12px;border-radius:8px;background:#173a2b;color:#c6f6dc;font-weight:750;">Testable Hypothesis</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("### The Evidence we used")
    st.markdown("""
    <div style="margin:8px 0 16px;padding:13px 16px;border-radius:10px;background:#172d43;border-left:4px solid #58a6ff;">
      <div style="font-size:1rem;line-height:1.55;color:#f0f6fc;font-weight:750;">Why these Datasets?</div>
      <div style="font-size:1rem;line-height:1.6;color:#d5e2ef;margin-top:3px;">Each source answers a different part of the question. Together they give us context, a way to demonstrate analysis, and a view of existing solutions. None can prove the whole market opportunity on its own.</div>
    </div>
    """, unsafe_allow_html=True)
    sources = [
        ("RBI Reported Fraud", "30 monthly observations", "Sep 2022 to Feb 2025", "Shows reported domestic payment-fraud volume, amount involved and related indicators. It is not UPI-only data.", "#2E86DE"),
        ("NPCI UPI Activity", "48 monthly observations", "Apr 2022 to Mar 2026", "Shows UPI transaction scale, value and ecosystem participation. It is not a fraud numerator.", "#17A589"),
        ("Synthetic Transactions", "20,000 generated rows", "Transaction file + label file", "Lets us demonstrate data checks and explore risk signals. The labels are generated, not real fraud outcomes.", "#9B59B6"),
        ("Market and Vendor Research", "Public descriptions and case studies", "Commercial + public initiatives", "Helps map existing alternatives and questions to test. Marketing claims are not treated as independently proven ROI.", "#E67E22"),
    ]
    src_cols = st.columns(4)
    for col, (heading, count, period, body, accent) in zip(src_cols, sources):
        with col:
            st.markdown(f"""
            <div style="height:100%;min-height:205px;border-top:4px solid {accent};border-radius:10px;padding:16px;background:#171c24;border-left:1px solid #303844;border-right:1px solid #303844;border-bottom:1px solid #303844;">
              <div style="font-size:1rem;font-weight:750;color:#f4f6f8;">{heading}</div>
              <div style="font-size:1.05rem;font-weight:750;color:{accent};margin-top:12px;">{count}</div>
              <div style="font-size:.82rem;color:#aeb8c5;margin-top:3px;">{period}</div>
              <div style="font-size:.9rem;line-height:1.5;color:#d3dae3;margin-top:12px;">{body}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.markdown("### What was Cleaned and Checked")
    st.markdown("""
    <div style="margin:8px 0 16px;padding:13px 16px;border-radius:10px;background:#172d43;border-left:4px solid #58a6ff;">
      <div style="font-size:1rem;line-height:1.55;color:#f0f6fc;font-weight:750;">Why Clean And Validate The Data?</div>
      <div style="font-size:1rem;line-height:1.6;color:#d5e2ef;margin-top:3px;">Before using the numbers, I checked dates, missing values, duplicates, units and whether the transaction IDs and labels matched. This makes the analysis more reliable, but it does not make the data representative or prove a business claim.</div>
    </div>
    """, unsafe_allow_html=True)
    clean_cols = st.columns(4)
    checks = [
        ("Dates and Structure", "Parsed month fields consistently and checked that monthly coverage made sense."),
        ("Numeric Measures", "Converted source values into numeric fields and checked the UPI average transaction value unit conversion."),
        ("Missing Values and Duplicates", "Checked gaps, duplicate months, duplicate transaction IDs and missing cells."),
        ("Cross-File Reconciliation", "Matched transaction IDs and compared the generated fraud labels across both CSV files."),
    ]
    for col, (heading, body) in zip(clean_cols, checks):
        with col:
            st.markdown(f"**{heading}**")
            st.write(body)

    quality = []
    if rbi is not None:
        expected = pd.date_range(rbi["month"].min(), rbi["month"].max(), freq="MS")
        quality.append({"Dataset": "RBI Reported Fraud", "Rows": len(rbi), "Coverage": f"{rbi.month.min():%b %Y} to {rbi.month.max():%b %Y}", "Validation": f"{rbi.month.nunique()} unique months · {len(expected.difference(pd.DatetimeIndex(rbi.month)))} missing months · {int(rbi.isna().sum().sum())} blank cells"})
    if upi is not None:
        expected = pd.date_range(upi["Month"].min(), upi["Month"].max(), freq="MS")
        quality.append({"Dataset": "NPCI UPI Activity", "Rows": len(upi), "Coverage": f"{upi['Month'].min():%b %Y} to {upi['Month'].max():%b %Y}", "Validation": f"{upi['Month'].nunique()} unique months · {len(expected.difference(pd.DatetimeIndex(upi['Month'])))} missing months · {int(upi.isna().sum().sum())} blank cells"})
    if tx is not None:
        quality.append({"Dataset": "Synthetic Transactions", "Rows": len(tx), "Coverage": "Generated sample", "Validation": f"{int(tx['transaction_id'].duplicated().sum())} duplicate IDs · {int(tx.isna().sum().sum()):,} blank cells"})
    if labels is not None and recon is not None:
        quality.append({"Dataset": "Synthetic Fraud Labels", "Rows": len(labels), "Coverage": "Generated sample", "Validation": f"{int((~recon['label_match'].fillna(False)).sum())} ID/label mismatches · {int(labels['transaction_id'].duplicated().sum())} duplicate label IDs"})
    if quality:
        st.dataframe(pd.DataFrame(quality), hide_index=True, use_container_width=True)
    if load_error:
        st.error(f"A data file could not be loaded: {load_error}")
    missing_files = [key for key, value in paths.items() if value is None]
    if missing_files:
        st.warning("Files not found beside app.py: " + ", ".join(missing_files) + ". Save the supplied data files in the same project folder.")

    st.warning("**Keep this distinction in mind:** the RBI series and UPI activity series describe different populations. The synthetic sample is generated data. These are useful research inputs, but they cannot be combined into a real UPI fraud rate.")

    st.divider()
    st.markdown("### Where the Research landed")
    left, right = st.columns([1.3, 1])
    with left:
        st.write("The most testable direction so far is a narrow workflow problem at financial institutions: evidence retrieval, response preparation, exception routing and complaint or law-enforcement request handling.")
        st.write("Why focus here? It is specific enough to validate with buyers and to model. It is not the same as building another transaction-level fraud detection engine.")
    with right:
        st.markdown("""
        <div style="border:1px solid #5a4a25;background:#302817;border-radius:12px;padding:18px;">
          <div style="font-size:.82rem;text-transform:uppercase;letter-spacing:.08em;font-weight:750;color:#f6c66b;">Current Call</div>
          <div style="font-size:1.25rem;font-weight:800;color:#fff4d8;margin:8px 0;">Explore Further. Do not launch yet.</div>
          <div style="color:#e8ddc5;line-height:1.5;">We still need buyer interviews, real workflow baselines, cost estimates and a measured pilot.</div>
        </div>
        """, unsafe_allow_html=True)
    st.caption("This is a structured first point of view, not a final verdict. The value is in making the evidence, assumptions and next questions visible.")

with market_tab:
    st.markdown("### Two Different Lenses: Reported Fraud and UPI Growth")
    st.caption("What this page is trying to show: how reported fraud indicators and UPI activity moved over time, without pretending they measure the same thing.")
    st.caption("Each dot is one observed monthly value from the source data. The chart does not create in-between monthly observations or interpolate missing data.")
    left, right = st.columns(2)
    with left:
        st.markdown("**RBI · Reported Domestic Payment Fraud**")
        if rbi is None:
            st.warning("RBI workbook not found beside app.py.")
        else:
            rbi_metrics = {
                "amount_involved_crore": "Amount involved (₹ crore)",
                "fraud_volume_lakh": "Reported fraud volume (lakh)",
                "one_in_x_transactions": "One in every X transactions (higher X = lower implied frequency)",
                "fts_bps": "Fraud-to-payment value (bps)",
            }
            rbi_measure = st.selectbox("Choose an RBI measure", list(rbi_metrics), format_func=lambda x: rbi_metrics[x], key="rbi_measure")
            fig = px.scatter(rbi, x="month", y=rbi_measure, title=rbi_metrics[rbi_measure], labels={"month": "Month", rbi_measure: rbi_metrics[rbi_measure]})
            fig.update_traces(marker={"size": 8})
            fig.update_layout(margin=dict(l=10, r=10, t=55, b=10))
            st.plotly_chart(fig, use_container_width=True)
            start, end = rbi.iloc[0], rbi.iloc[-1]
            change = (end[rbi_measure] / start[rbi_measure] - 1) * 100 if start[rbi_measure] else np.nan
            st.caption(f"{len(rbi)} observed months · {start.month:%b %Y} to {end.month:%b %Y} · endpoint change: {change:+.1f}% (descriptive only)")
    with right:
        st.markdown("**NPCI · UPI Ecosystem Activity**")
        if upi is None:
            st.warning("UPI workbook not found beside app.py.")
        else:
            upi_metrics = {
                "Volume (In Mn.)": "Monthly Transaction Volume (Million)",
                "Value (In Cr.)": "Monthly Transaction Value (₹ Crore)",
                "Banks live on UPI": "Banks Live On UPI",
                "avg_transaction_value_rupees": "Implied average transaction value (₹)",
            }
            upi_measure = st.selectbox("Choose a UPI measure", list(upi_metrics), format_func=lambda x: upi_metrics[x], key="upi_measure")
            fig = px.scatter(upi, x="Month", y=upi_measure, title=upi_metrics[upi_measure], labels={"Month": "Month", upi_measure: upi_metrics[upi_measure]})
            fig.update_traces(marker={"size": 8})
            fig.update_layout(margin=dict(l=10, r=10, t=55, b=10))
            st.plotly_chart(fig, use_container_width=True)
            if len(upi) >= 13:
                last, prior = upi.iloc[-1], upi.iloc[-13]
                v_growth = (last["Volume (In Mn.)"] / prior["Volume (In Mn.)"] - 1) * 100
                val_growth = (last["Value (In Cr.)"] / prior["Value (In Cr.)"] - 1) * 100
                st.caption(f"Latest month: {last['Month']:%b %Y} · volume YoY {v_growth:+.1f}% · value YoY {val_growth:+.1f}%")

    st.divider()
    st.markdown("### The Notebook Comparison: Indexed Trends")
    st.markdown("**Why index the series?** Different measures have different units. Setting the first shared month to 100 lets us compare how each series moved relative to its own starting point, not compare their absolute sizes.")
    if rbi is not None and upi is not None:
        common = upi.merge(rbi, left_on="Month", right_on="month", how="inner").sort_values("Month").copy()
        if not common.empty:
            base = common.iloc[0]
            common["UPI transaction volume index"] = common["Volume (In Mn.)"] / base["Volume (In Mn.)"] * 100
            common["UPI transaction value index"] = common["Value (In Cr.)"] / base["Value (In Cr.)"] * 100
            common["Reported fraud volume index"] = common["fraud_volume_lakh"] / base["fraud_volume_lakh"] * 100
            common["Reported fraud amount index"] = common["amount_involved_crore"] / base["amount_involved_crore"] * 100
            common["FTS index"] = common["fts_bps"] / base["fts_bps"] * 100
            st.caption(f"Common window: {common['Month'].min():%b %Y}–{common['Month'].max():%b %Y} · {len(common)} matched monthly observations · base month = 100")
            c1, c2 = st.columns(2)
            with c1:
                upi_index_cols = ["UPI transaction volume index", "UPI transaction value index"]
                plot_upi = common.melt(id_vars="Month", value_vars=upi_index_cols, var_name="Series", value_name="Index")
                fig = px.scatter(plot_upi, x="Month", y="Index", color="Series", title="UPI activity expanded substantially", labels={"Month": "Month", "Index": "Index (base = 100)"})
                fig.update_traces(marker={"size": 7})
                fig.update_layout(margin=dict(l=10, r=10, t=55, b=10))
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                rbi_index_cols = ["Reported fraud volume index", "Reported fraud amount index", "FTS index"]
                plot_rbi = common.melt(id_vars="Month", value_vars=rbi_index_cols, var_name="Series", value_name="Index")
                fig = px.scatter(plot_rbi, x="Month", y="Index", color="Series", title="RBI-reported fraud indicators fluctuated", labels={"Month": "Month", "Index": "Index (base = 100)"})
                fig.update_traces(marker={"size": 7})
                fig.update_layout(margin=dict(l=10, r=10, t=55, b=10))
                st.plotly_chart(fig, use_container_width=True)
            end = common.iloc[-1]
            summary = pd.DataFrame([
                {"Series": "UPI transaction volume", "Base index": 100.0, "Latest index": end["UPI transaction volume index"], "Change from base (%)": end["UPI transaction volume index"] - 100},
                {"Series": "UPI transaction value", "Base index": 100.0, "Latest index": end["UPI transaction value index"], "Change from base (%)": end["UPI transaction value index"] - 100},
                {"Series": "RBI reported fraud volume", "Base index": 100.0, "Latest index": end["Reported fraud volume index"], "Change from base (%)": end["Reported fraud volume index"] - 100},
                {"Series": "RBI reported fraud amount", "Base index": 100.0, "Latest index": end["Reported fraud amount index"], "Change from base (%)": end["Reported fraud amount index"] - 100},
                {"Series": "FTS", "Base index": 100.0, "Latest index": end["FTS index"], "Change from base (%)": end["FTS index"] - 100},
            ])
            st.dataframe(summary.round(2), hide_index=True, use_container_width=True)
            # Translate the indexed chart into a plain-English takeaway using the actual common-window endpoints.
            upi_vol_change = end["UPI transaction volume index"] - 100
            upi_val_change = end["UPI transaction value index"] - 100
            fraud_vol_change = end["Reported fraud volume index"] - 100
            fraud_amt_change = end["Reported fraud amount index"] - 100
            fts_change = end["FTS index"] - 100
            st.markdown("#### So, What Should We Take Away?")
            st.markdown(
                f"""
                <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:8px 0 14px;">
                  <div style="padding:15px;border:1px solid #2d7054;border-radius:12px;background:#152c23;">
                    <div style="font-size:.78rem;font-weight:800;color:#80e0b1;">PAYMENT ACTIVITY</div>
                    <div style="font-size:1.35rem;font-weight:850;color:#f3fff8;margin:8px 0;">Volume +{upi_vol_change:.1f}%</div>
                    <div style="color:#cde6d9;line-height:1.5;">UPI volume grew faster than UPI value, which means the mix of average transaction value also changed.</div>
                  </div>
                  <div style="padding:15px;border:1px solid #80652e;border-radius:12px;background:#302717;">
                    <div style="font-size:.78rem;font-weight:800;color:#f6ce77;">REPORTED FRAUD</div>
                    <div style="font-size:1.12rem;font-weight:850;color:#fff7e4;margin:8px 0;">Volume +{fraud_vol_change:.1f}% · Amount +{fraud_amt_change:.1f}%</div>
                    <div style="color:#e9dec6;line-height:1.5;">Reported fraud measures rose by less than UPI activity in this index comparison, but they cover different populations.</div>
                  </div>
                  <div style="padding:15px;border:1px solid #4a5060;border-radius:12px;background:#20242d;">
                    <div style="font-size:.78rem;font-weight:800;color:#cbd5e1;">THE LIMIT</div>
                    <div style="font-size:1.12rem;font-weight:850;color:#f5f7fa;margin:8px 0;">FTS {fts_change:+.1f}%</div>
                    <div style="color:#d0d5de;line-height:1.5;">A different movement across measures is a prompt to investigate, not proof that UPI is safer or that a vendor can prevent the difference.</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.info("**Business implication:** the scale of digital payments makes fraud management worth examining, but this chart does not identify the buyer, the unmet need, preventable loss or willingness to pay. We need buyer-level evidence for those questions.")
            st.caption("The synthetic transaction dataset is not used to calculate these indices or to infer real-world fraud trends.")
    else:
        st.warning("Both RBI and UPI files are needed to build the indexed comparison.")

with synthetic_tab:
    st.markdown("### Synthetic Transaction Exploration")
    st.caption("Why this page exists: Demonstrate the analysis workflow and data-quality checks. It cannot tell us the real-world fraud rate or which app is safest.")
    st.caption("This dataset is a sandbox for demonstrating analysis, not a sample of real UPI transactions.")
    st.markdown("""
    <div style="padding:16px 18px;border:1px solid #35546e;border-radius:12px;background:#152635;margin:10px 0 16px;">
      <div style="font-size:.8rem;font-weight:800;letter-spacing:.08em;color:#80c5ff;">WHY INCLUDE SYNTHETIC DATA AT ALL?</div>
      <div style="font-size:1.05rem;font-weight:800;color:#f4f8fc;margin:8px 0;">To show the analysis method, not to prove a fraud pattern.</div>
      <div style="color:#d1deeb;line-height:1.55;">We used it to practise checking data quality, reconciling labels, measuring missingness, segmenting transactions and calculating group-level rates. Because the labels were generated from risk signals, relationships between those signals and the labels are partly built into the dataset. They are not independent evidence of real fraud behaviour.</div>
    </div>
    """, unsafe_allow_html=True)
    if tx is None or labels is None or recon is None:
        st.warning("Both synthetic CSV files must be present beside app.py, with transaction_id and is_fraud columns.")
    else:
        n = len(tx)
        nf = int(pd.to_numeric(tx["is_fraud"], errors="coerce").fillna(0).sum())
        a, b, c, d = st.columns(4)
        a.metric("Transaction rows", f"{n:,}")
        b.metric("Fraud-labelled rows", f"{nf:,}", f"{nf/n*100:.2f}%" if n else None)
        c.metric("Duplicate transaction IDs", f"{int(tx['transaction_id'].duplicated().sum()):,}")
        d.metric("ID/label mismatches", f"{int((~recon['label_match'].fillna(False)).sum()):,}")
        st.error("The labels were generated from risk signals. Their 3.82% rate and any signal relationships do not estimate real-world UPI fraud, prove control effectiveness, or support ranking actual payment apps.")
        miss = tx.isna().sum()
        miss = miss[miss > 0]
        if not miss.empty:
            st.markdown("**Missing Values:** missing risk signals are left visible rather than silently replaced with zero.")
            st.dataframe(miss.rename("Missing cells").rename_axis("Column").reset_index(), hide_index=True, use_container_width=True)
        if "amount" in tx.columns:
            amount = tx.assign(label=tx["is_fraud"].map({0: "Non-fraud-labelled", 1: "Fraud-labelled"})).groupby("label").agg(
                transactions=("transaction_id", "count"), total_transaction_value=("amount", "sum"),
                mean_amount=("amount", "mean"), median_amount=("amount", "median")
            ).reset_index()
            st.markdown("**Transaction Value By Generated Label** (not confirmed fraud loss or preventable loss)")
            st.dataframe(amount.round(2), hide_index=True, use_container_width=True)
        signals = [x for x in ["new_device_flag", "ip_location_mismatch", "failed_attempts_last_24h", "is_night_transaction"] if x in tx.columns]
        if signals:
            sig = st.selectbox("Explore generated label rate by signal", signals)
            temp = tx.copy()
            if sig in ["new_device_flag", "ip_location_mismatch", "is_night_transaction"]:
                temp[sig] = temp[sig].map({0: "No", 1: "Yes"}).fillna("Missing")
            else:
                temp[sig] = np.where(temp[sig].isna(), "Missing", np.where(temp[sig] > 0, "One or more", "None"))
            tab = temp.groupby(sig, dropna=False).agg(records=("transaction_id", "count"), fraud_label_rate=("is_fraud", "mean")).reset_index()
            tab["fraud_label_rate_pct"] = tab["fraud_label_rate"] * 100
            fig = px.bar(tab, x=sig, y="fraud_label_rate_pct", text="records", title=f"Generated label rate by {sig}")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(tab.drop(columns="fraud_label_rate").round(2), hide_index=True, use_container_width=True)
            st.markdown("#### What do we do with this Analysis?")
            st.markdown("""
            <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:8px 0 14px;">
              <div style="padding:14px;border:1px solid #343b46;border-radius:11px;background:#171c24;"><div style="font-weight:800;color:#f4f6f8;">1. Demonstrate The Workflow</div><div style="color:#cbd3dd;line-height:1.5;margin-top:7px;">Check IDs, missing values, label balance and differences between groups.</div></div>
              <div style="padding:14px;border:1px solid #6c5729;border-radius:11px;background:#2b2416;"><div style="font-weight:800;color:#f6ce77;">2. Learn What Real Data Must Contain</div><div style="color:#e6dcc6;line-height:1.5;margin-top:7px;">Reliable outcomes, time windows, transaction context and clear definitions of fraud and loss.</div></div>
              <div style="padding:14px;border:1px solid #8b4545;border-radius:11px;background:#321d21;"><div style="font-weight:800;color:#ffaaaa;">3. Do Not Use It To Claim A Market Gap</div><div style="color:#ead0d0;line-height:1.5;margin-top:7px;">These results do not support real fraud rates, provider rankings, control effectiveness or our final commercial recommendation.</div></div>
            </div>
            """, unsafe_allow_html=True)
            st.info("**How this connects to the wider project:** This synthetic dataset is a methods demonstration only. The opportunity hypothesis comes from the desk research and must be tested with real bank workflows, buyer interviews and baseline operating data. We do not use these generated labels to justify the post-complaint workflow idea.")

with economics_tab:
    st.markdown("### Could a Workflow tool pay for itself?")
    st.caption("The question: how much work might be freed up, what would that capacity be worth, and would it cover the software and implementation costs?")
    st.markdown("This is a **what-if calculator**, not a forecast. The starting numbers are illustrative assumptions, not bank-validated data or a vendor quote.")
    st.markdown("**Use this page to test the business case, not to claim that a bank will save this amount.**")

    with st.expander("How The Calculator Works", expanded=True):
        st.markdown("""
        1. **Current annual processing cost** = cases per year × manual hours per case × loaded labour cost per hour.
        2. **Annual hours released** = cases per year × share covered by the tool × hours per case × effort saved on covered cases.
        3. **Gross capacity value** = annual hours released × loaded labour cost per hour.
        4. **Modelled recurring value after fee** = gross capacity value minus annual solution cost.
        5. **First-year modelled value** = recurring value after fee minus one-time implementation cost.
        """)
        st.caption("Important: capacity value is not automatically cash savings. It becomes a realised financial benefit only if costs are reduced, hiring is avoided, or the freed-up time is productively redeployed. The model also excludes taxes, financing, change-management costs and any benefits not entered here.")

    st.markdown("#### 1. Set the Operating Assumptions")
    c1, c2, c3 = st.columns(3)
    cases = c1.number_input("Cases Handled Per Year", min_value=0, value=50000, step=5000, help="Annual complaint or request volume for the workflow being tested.")
    hours = c2.number_input("Manual Hours Per Case", min_value=0.0, value=0.75, step=0.05, help="Average staff time spent on one case today.")
    rate = c3.number_input("Loaded Labour Cost Per Hour (₹)", min_value=0, value=1000, step=100, help="Illustrative hourly cost including relevant employment overheads.")
    c4, c5, c6 = st.columns(3)
    coverage = c4.slider("Share Of Cases The Tool Can Cover", 0, 100, 50, 5, help="The proportion of total cases eligible for automation.") / 100
    reduction = c5.slider("Effort Saved On Covered Cases", 0, 100, 40, 5, help="The share of manual effort removed from the cases the tool covers.") / 100
    annual_fee = c6.number_input("Annual Solution Cost (₹ Lakh)", min_value=0.0, value=35.0, step=5.0, help="Illustrative annual licence and operating cost.")
    implementation = st.number_input("One-Time Implementation Cost (₹ Lakh)", min_value=0.0, value=30.0, step=5.0, help="Illustrative setup, integration and implementation cost.")

    current = cases * hours * rate / 100000
    hours_released = cases * coverage * hours * reduction
    gross = hours_released * rate / 100000
    net = gross - annual_fee
    first_year = net - implementation
    payback = implementation / net * 12 if net > 0 else None
    covered_cases = cases * coverage

    st.markdown("#### 2. Read the Output")
    st.caption("All money figures below are in ₹ lakh per year unless labelled otherwise.")
    a, b, c, d = st.columns(4)
    a.metric("Current Annual Processing Cost", f"₹{current:,.1f} Lakh")
    b.metric("Estimated Hours Released", f"{hours_released:,.0f} Hrs", help=f"Based on {covered_cases:,.0f} cases covered and {reduction:.0%} effort saved on those cases.")
    c.metric("Gross Capacity Value", f"₹{gross:,.1f} Lakh")
    d.metric("Value After Annual Fee", f"₹{net:,.1f} Lakh", help="Gross capacity value minus annual solution cost. This is not guaranteed cash savings.")

    e, f = st.columns(2)
    e.metric("First-Year Value After all Listed Costs", f"₹{first_year:,.1f} Lakh", help="Gross capacity value minus annual solution cost and one-time implementation cost.")
    if payback is None:
        f.metric("Simple Implementation Payback", "Not Reached")
    else:
        f.metric("Simple Implementation Payback", f"{payback:.1f} Months", help="Implementation cost divided by modelled annual value after the annual fee, converted to months. Assumes benefits arrive evenly and are fully realised.")

    if gross < annual_fee:
        st.error(f"At these assumptions, the modelled capacity value (₹{gross:,.1f} lakh) does not cover the annual solution fee (₹{annual_fee:,.1f} lakh). The recurring case does not break even.")
    elif first_year < 0:
        st.warning("The modelled annual capacity value covers the recurring fee, but not the one-time implementation cost in year one. The business case depends on sustained benefits in later years and on those benefits being realised.")
    else:
        st.success("The assumptions produce a positive modelled first-year value. Treat this as a hypothesis to validate, not a confirmed saving.")

    st.markdown("#### 3. What would need to be True in a Real Bank?")
    gate1, gate2, gate3 = st.columns(3)
    gate1.markdown("**Baseline**\n\nConfirm case volume, time per case, backlog, rework and loaded staff cost using actual workflow data.")
    gate2.markdown("**Feasibility**\n\nMeasure what share of cases can actually be automated, how much time is saved, and what exceptions still need a person.")
    gate3.markdown("**Value Capture**\n\nConfirm whether released time reduces spend, avoids hiring, improves turnaround or can be redeployed to higher-value work.")
    st.caption("The base case is 50,000 cases, 0.75 hours per case, ₹1,000 per hour, 50% coverage, 40% effort reduction, ₹35 lakh annual solution cost and ₹30 lakh implementation. These assumptions are illustrative and have not been validated with a bank.")

with competition_tab:
    st.markdown("### Existing Solutions: What are we up against?")
    st.caption("Why this page exists: To comprehend if the proposed idea is genuinely different from what banks can already buy or access. A new product needs a clear gap, not just a fresh AI label.")
    st.markdown("#### Commercial Platforms already cover a lot!")
    st.write("These vendors describe established fraud-decisioning capabilities. Their claims help us map the market, but they are not a like-for-like benchmark and do not prove performance in every Indian bank.")
    vendor_cols = st.columns(3)
    vendors = [
        {
            "name": "SAS Fraud Decisioning", "tag": "RULES + REAL-TIME DECISIONS", "color": "#2E86DE",
            "headline": "Connect signals. Make decisions.",
            "detail": "Markets real-time scoring, business rules, data orchestration, alert triage and investigation workflows.",
            "question": "Could an existing platform already cover the buyer's need through configuration or integration?"
        },
        {
            "name": "Feedzai", "tag": "AI + CONTEXTUAL RISK", "color": "#17A589",
            "headline": "Read more than the payment.",
            "detail": "Markets AI-led fraud and financial-crime detection using behavioural, device, network and transaction context, with analysts remaining in the loop.",
            "question": "What extra signals or workflow outcomes would be incremental to what the institution already has?"
        },
        {
            "name": "Featurespace", "tag": "ADAPTIVE BEHAVIOUR ANALYTICS", "color": "#9B59B6",
            "headline": "Spot behaviour that looks unusual.",
            "detail": "Emphasises adaptive behavioural analytics and modelling deviations from normal customer or transaction behaviour.",
            "question": "Are published performance claims relevant to this buyer, use case and operating setup?"
        },
    ]
    for col, vendor in zip(vendor_cols, vendors):
        with col:
            st.markdown(f"""
            <div style="height:100%;min-height:340px;border:1px solid #343b46;border-top:5px solid {vendor['color']};border-radius:14px;background:#171c24;padding:19px;">
              <div style="font-size:.72rem;letter-spacing:.08em;font-weight:800;color:{vendor['color']};">{vendor['tag']}</div>
              <div style="font-size:1.28rem;line-height:1.25;font-weight:850;color:#fff;margin:12px 0 8px;">{vendor['name']}</div>
              <div style="font-size:1rem;font-weight:750;color:#e4edf7;margin-bottom:12px;">{vendor['headline']}</div>
              <div style="font-size:.92rem;line-height:1.55;color:#cbd3dd;">{vendor['detail']}</div>
              <div style="margin-top:18px;padding:12px;border-radius:9px;background:#222c38;color:#dbe8f5;font-size:.88rem;line-height:1.5;"><b>Question For Our Research</b><br>{vendor['question']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### Shared Intelligence is also part of the picture")
    st.write("Not every alternative is a vendor platform. Public and shared-intelligence initiatives may provide signals that banks can use alongside their own controls. These are different layers, and we should not assume a specific bank's architecture without evidence.")
    infra_cols = st.columns(2)
    with infra_cols[0]:
        st.markdown("""
        <div style="border:1px solid #35546e;border-radius:12px;padding:18px;background:#152635;min-height:205px;">
          <div style="font-size:.78rem;font-weight:800;letter-spacing:.08em;color:#80c5ff;">TELECOM-LINKED INTELLIGENCE</div>
          <div style="font-size:1.2rem;font-weight:850;color:#fff;margin:8px 0;">FRI / DoT DIP</div>
          <div style="color:#d1deeb;line-height:1.55;">Designed to share telecom-linked risk intelligence with participating institutions. Government-reported impact figures should be labelled as reported, not treated as independently audited ROI.</div>
        </div>
        """, unsafe_allow_html=True)
    with infra_cols[1]:
        st.markdown("""
        <div style="border:1px solid #4d466f;border-radius:12px;padding:18px;background:#211d31;min-height:205px;">
          <div style="font-size:.78rem;font-weight:800;letter-spacing:.08em;color:#c1a8ff;">CROSS-INSTITUTION FRAUD INTELLIGENCE</div>
          <div style="font-size:1.2rem;font-weight:850;color:#fff;margin:8px 0;">DPIP / IDPIC</div>
          <div style="color:#dcd6ec;line-height:1.55;">Designed to connect defined fraud signals across participating financial institutions. Public descriptions outline intended capabilities, but do not establish independently verified impact or buyer ROI.</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### So, Where could a Real Opportunity be?")
    st.markdown("""
    <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;">
      <div style="padding:16px;border:1px solid #3a414b;border-radius:12px;background:#171c24;"><div style="font-weight:800;color:#f5f7fa;">Probably Not Enough</div><div style="color:#cbd3dd;margin-top:8px;line-height:1.5;">"We use AI to detect fraud." Existing vendors already market this.</div></div>
      <div style="padding:16px;border:1px solid #6c5729;border-radius:12px;background:#2b2416;"><div style="font-weight:800;color:#f6ce77;">Worth Testing</div><div style="color:#e6dcc6;margin-top:8px;line-height:1.5;">A specific, costly workflow that current systems do not handle well enough.</div></div>
      <div style="padding:16px;border:1px solid #3a414b;border-radius:12px;background:#171c24;"><div style="font-weight:800;color:#f5f7fa;">Must Be Proven</div><div style="color:#cbd3dd;margin-top:8px;line-height:1.5;">A measurable improvement, workable integration and a buyer willing to pay.</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("**Current read:** The generic fraud-detection space is already well served on paper. A narrower post-complaint workflow idea may be worth buyer discovery, but we have not yet shown that it is a market gap.")
    st.markdown("#### What we still need to find out")
    unknowns = [
        "Which Indian institutions have this problem, and how often does it happen?",
        "What do current workflows cost in staff time, rework and missed service levels?",
        "What can existing internal tools, vendors and shared infrastructure already automate?",
        "What would implementation, integration, security review and ongoing support cost?",
        "Who owns the budget, and would they pay for a measurable improvement?",
    ]
    for item in unknowns:
        st.markdown(f"- {item}")
    st.caption("Vendor-reported outcomes are directional unless independently verified. They are not assumed to be comparable across vendors or representative of India-wide performance.")

with decision_tab:
    st.markdown("### Recommendation And Evidence: What Should Happen Next?")
    st.caption("Why this page exists: Turn the research into a clear decision, show how confident we should be, and make the next evidence-gathering steps practical.")
    st.markdown("""
    <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:8px 0 18px;">
      <div style="padding:17px;border-radius:12px;border:1px solid #2d7054;background:#152c23;"><div style="font-size:.78rem;font-weight:800;letter-spacing:.08em;color:#80e0b1;">WHAT WE KNOW</div><div style="font-size:1.05rem;font-weight:800;color:#f3fff8;margin:9px 0;">Activity Is Growing</div><div style="color:#cde6d9;line-height:1.5;">UPI is scaling. RBI also reports domestic payment fraud. The series are useful context, not directly comparable populations.</div></div>
      <div style="padding:17px;border-radius:12px;border:1px solid #80652e;background:#302717;"><div style="font-size:.78rem;font-weight:800;letter-spacing:.08em;color:#f6ce77;">WHAT WE SUSPECT</div><div style="font-size:1.05rem;font-weight:800;color:#fff7e4;margin:9px 0;">Workflow Friction May Exist</div><div style="color:#e9dec6;line-height:1.5;">Selected complaint and evidence-handling tasks may be costly or slow. This still needs direct buyer validation.</div></div>
      <div style="padding:17px;border-radius:12px;border:1px solid #4a5060;background:#20242d;"><div style="font-size:.78rem;font-weight:800;letter-spacing:.08em;color:#cbd5e1;">WHAT WE CANNOT CLAIM</div><div style="font-size:1.05rem;font-weight:800;color:#f5f7fa;margin:9px 0;">No Proven Market Gap Yet</div><div style="color:#d0d5de;line-height:1.5;">No validated demand, independent ROI, India-wide market sizing or product-launch case has been established.</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("#### The Current Call")
    st.markdown("**Specific next move:** Do not build a generic fraud-detection product yet. First test whether Indian banks have a costly, repetitive post-complaint workflow that existing tools do not already solve well enough.")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("""
        <div style="height:100%;padding:20px;border:1px solid #2d7054;border-radius:13px;background:#152c23;">
          <div style="font-size:.8rem;letter-spacing:.1em;font-weight:850;color:#80e0b1;">GO</div>
          <div style="font-size:1.25rem;font-weight:850;color:#f3fff8;margin:8px 0;">Continue Commercial Diligence</div>
          <div style="color:#cde6d9;line-height:1.55;">Test the selected post-complaint workflow hypothesis with real bank teams, baseline data and implementation estimates.</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div style="height:100%;padding:20px;border:1px solid #8b4545;border-radius:13px;background:#321d21;">
          <div style="font-size:.8rem;letter-spacing:.1em;font-weight:850;color:#ffaaaa;">NO-GO FOR NOW</div>
          <div style="font-size:1.25rem;font-weight:850;color:#fff2f2;margin:8px 0;">Do Not Recommend Product Launch</div>
          <div style="color:#ead0d0;line-height:1.55;">The current evidence does not support launching another generic transaction-fraud detection product.</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### Make the Next Step Specific")
    st.caption("The first milestone is evidence collection, not software development. A buyer conversation should establish whether the problem exists, how it is handled today, and whether improvement is valuable enough to fund.")
    validation_rows = [
        {"Question To Validate": "Where does work get stuck?", "Who To Ask": "Fraud operations, complaint handling and law-enforcement liaison teams", "Evidence To Request": "An anonymised workflow map, case categories and examples of hand-offs or rework"},
        {"Question To Validate": "How big is the problem?", "Who To Ask": "Process owner and operations manager", "Evidence To Request": "Monthly case volumes, time per case, backlog, turnaround time and SLA misses"},
        {"Question To Validate": "Is the gap already solved?", "Who To Ask": "Technology, fraud platform owner and operations users", "Evidence To Request": "Current tools, automation coverage, integrations, manual exceptions and known limitations"},
        {"Question To Validate": "Would a solution pay off?", "Who To Ask": "Budget owner, finance and procurement", "Evidence To Request": "Implementation estimate, annual run cost, measurable capacity or cash benefit, and buying process"},
    ]
    st.dataframe(pd.DataFrame(validation_rows), hide_index=True, use_container_width=True)
    st.markdown("**Decision gate:** Only move to a pilot if a real buyer confirms a recurring pain point, baseline data can be measured, the current stack leaves a specific gap, and the estimated incremental benefit can be compared with full implementation and operating costs.")
    st.divider()
    st.markdown("#### The Next Steps, In Order")
    steps = [
        ("1", "Talk to Buyers", "Fraud operations, complaint teams, legal or law-enforcement liaison, technology, risk and procurement."),
        ("2", "Get the Baseline", "Annual case volumes, time per case, rework, SLA misses, escalation rates and cost per case."),
        ("3", "Map the Current Stack", "What internal tools, vendors and shared-intelligence systems already do, and where work still falls through."),
        ("4", "Price the Solution", "Integration effort, security requirements, implementation timeline, annual fee and support cost."),
        ("5", "Run a Measured Pilot", "Track turnaround time, quality, workload, exception rates and cash-realised savings or redeployment."),
    ]
    step_cols = st.columns(5)
    for col, (num, heading, body) in zip(step_cols, steps):
        with col:
            st.markdown(f"""
            <div style="height:100%;min-height:195px;padding:15px;border:1px solid #343b46;border-radius:11px;background:#171c24;">
              <div style="font-size:1.6rem;font-weight:850;color:#80c5ff;">{num}</div>
              <div style="font-weight:800;color:#f4f6f8;margin:7px 0;">{heading}</div>
              <div style="font-size:.88rem;line-height:1.5;color:#cbd3dd;">{body}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### Evidence Register: What Each Input Can Actually Tell Us")
    st.write("This is the guardrail against overclaiming. Each source has a job, and each has a limit.")
    evidence_rows = [
        {"Evidence": "RBI Aggregate Series", "Useful For": "Reported domestic payment-fraud trends", "Cannot Establish": "UPI-only fraud rate, final victim loss, preventable loss or vendor opportunity"},
        {"Evidence": "NPCI UPI Monthly Series", "Useful For": "UPI activity scale and growth", "Cannot Establish": "Fraud incidence or causality"},
        {"Evidence": "Synthetic Transaction Sample", "Useful For": "Demonstrating data checks and exploratory analysis", "Cannot Establish": "Real-world fraud patterns, provider performance or control efficacy"},
        {"Evidence": "Vendor Claims and Case Studies", "Useful For": "Mapping marketed capabilities and research hypotheses", "Cannot Establish": "Independent ROI or comparable outcomes without validation"},
        {"Evidence": "Buyer Economics Simulator", "Useful For": "Identifying which assumptions drive a potential business case", "Cannot Establish": "Actual savings before baseline, pricing and pilot outcomes are known"},
    ]
    st.dataframe(pd.DataFrame(evidence_rows), hide_index=True, use_container_width=True)
    st.info("**The decision rule:** move forward only if buyers confirm the pain, the current stack leaves a real gap, and a measured pilot shows enough incremental value to justify the full cost.")

st.divider()
st.caption("Portfolio research prototype · Data cleaning improves consistency but does not establish representativeness or validate claims · No predictive fraud score is produced.")
