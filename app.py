import streamlit as st
import snowflake.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI

# ── Page config ──────────────────────────────────────────
st.set_page_config(
    page_title="MedTech Financial Intelligence",
    page_icon="🏥",
    layout="wide"
)

# ── Password protection ──────────────────────────────────
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🏥 MedTech Financial Intelligence")
        st.markdown("Please enter the password to access this app.")
        password = st.text_input("Password", type="password")
        if st.button("Enter"):
            if password == "medtronic2026":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
        st.stop()

check_password()

# ── Credentials ──────────────────────────────────────────
SNOWFLAKE_ACCOUNT   = st.secrets["SNOWFLAKE_ACCOUNT"]
SNOWFLAKE_USER      = st.secrets["SNOWFLAKE_USER"]
SNOWFLAKE_PASSWORD  = st.secrets["SNOWFLAKE_PASSWORD"]
SNOWFLAKE_DATABASE  = "MEDTECH_ANALYTICS"
SNOWFLAKE_WAREHOUSE = st.secrets["SNOWFLAKE_WAREHOUSE"]
OPENAI_API_KEY      = st.secrets["OPENAI_API_KEY"]

# ── Connections ──────────────────────────────────────────
@st.cache_resource
def get_snowflake_connection():
    return snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        database=SNOWFLAKE_DATABASE,
        warehouse=SNOWFLAKE_WAREHOUSE
    )

@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)

conn   = get_snowflake_connection()
client = get_openai_client()

# ── Data loaders ─────────────────────────────────────────
@st.cache_data
def load_financials():
    df = pd.read_sql(
        "SELECT * FROM MEDTECH_ANALYTICS.TRANSFORMED.VW_FINANCIALS_WIDE ORDER BY TICKER, YEAR",
        conn
    )
    return df

@st.cache_data
def load_growth():
    df = pd.read_sql(
        "SELECT * FROM MEDTECH_ANALYTICS.TRANSFORMED.VW_REVENUE_GROWTH ORDER BY TICKER, YEAR",
        conn
    )
    return df

@st.cache_data
def load_benchmark():
    df = pd.read_sql(
        "SELECT * FROM MEDTECH_ANALYTICS.TRANSFORMED.VW_BENCHMARK_LATEST",
        conn
    )
    return df

financials = load_financials()
growth     = load_growth()
benchmark  = load_benchmark()

# ── OpenAI helpers ───────────────────────────────────────
SCHEMA_CONTEXT = """
You are a financial data analyst assistant with access to a MedTech industry database in Snowflake.
Always use fully qualified table names in every query.

The database contains ONLY the following views and columns:

1. MEDTECH_ANALYTICS.TRANSFORMED.VW_FINANCIALS_WIDE
   Columns: TICKER, COMPANY, YEAR, REVENUE_B, OPERATING_INCOME_B, NET_INCOME_B, OPERATING_MARGIN_PCT, NET_MARGIN_PCT

2. MEDTECH_ANALYTICS.TRANSFORMED.VW_REVENUE_GROWTH
   Columns: TICKER, COMPANY, YEAR, REVENUE_B, PRIOR_YEAR_REVENUE_B, REVENUE_GROWTH_PCT

3. MEDTECH_ANALYTICS.TRANSFORMED.VW_BENCHMARK_LATEST
   Columns: TICKER, COMPANY, YEAR, REVENUE_B, OPERATING_INCOME_B, NET_INCOME_B, OPERATING_MARGIN_PCT, NET_MARGIN_PCT

Companies: Medtronic (MDT), Boston Scientific (BSX), Abbott (ABT), Stryker (SYK)
All revenue and income values are in billions USD. Years available: 2021 to 2025.

CRITICAL RULES:
- ONLY query columns that exist in the views above
- Gross margin, gross profit, EPS, EBITDA, R&D expense are NOT available — do not query them
- If a metric is not in the schema above, return this exact SQL: SELECT 'METRIC_NOT_AVAILABLE' AS ERROR
- Always use full path MEDTECH_ANALYTICS.TRANSFORMED.view_name in every query
- Respond with raw Snowflake SQL only — no explanation, no markdown, no backticks
"""

def nl_to_sql(question):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SCHEMA_CONTEXT},
            {"role": "user", "content": question}
        ],
        temperature=0
    )
    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql

def generate_narrative(question, df):
    data_str = df.to_string(index=False)
    prompt = f"""
You are a senior financial analyst writing a brief commentary for an executive audience.
Based on the following data, write a 3 sentence variance narrative that:
- States the key finding clearly with specific numbers from the data only
- Provides year over year or competitive context using only the data provided
- Highlights any trend or risk worth noting

IMPORTANT: Only use numbers that appear in the data below. Do not invent or estimate any figures.

Question: {question}
Data:
{data_str}

Write in professional financial analyst style. No bullet points. Do not use dollar signs — write currency as USD or spell out billions (e.g. 32.36 billion instead of $32.36B).
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def run_nl_query(question):
    sql = nl_to_sql(question)
    cursor = conn.cursor()
    cursor.execute(sql)
    df = pd.DataFrame(
        cursor.fetchall(),
        columns=[desc[0] for desc in cursor.description]
    )
    # Check if OpenAI flagged the metric as unavailable
    if "ERROR" in df.columns and df["ERROR"].iloc[0] == "METRIC_NOT_AVAILABLE":
        raise ValueError("metric_not_available")
    # Check if query returned no results
    if df.empty:
        raise ValueError("no_data")
    return df, sql

# ── Header ───────────────────────────────────────────────
st.title("🏥 MedTech Financial Intelligence")
st.markdown("**Medtronic · Boston Scientific · Abbott · Stryker** — 2021 to 2025 | Powered by SEC EDGAR + Snowflake + OpenAI")
st.divider()

# ── KPI Cards ────────────────────────────────────────────
st.subheader("2025 Snapshot — Medtronic")
mdt = benchmark[benchmark["TICKER"] == "MDT"].iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Revenue",           f"${mdt['REVENUE_B']}B")
col2.metric("Operating Margin",  f"{mdt['OPERATING_MARGIN_PCT']}%")
col3.metric("Net Income",        f"${mdt['NET_INCOME_B']}B")
col4.metric("Net Margin",        f"{mdt['NET_MARGIN_PCT']}%")

st.divider()

# ── Charts ───────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Revenue Trends (2021–2025)")
    fig_revenue = px.line(
        financials,
        x="YEAR",
        y="REVENUE_B",
        color="COMPANY",
        markers=True,
        labels={"REVENUE_B": "Revenue ($B)", "YEAR": "Year", "COMPANY": "Company"}
    )
    fig_revenue.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3))
    st.plotly_chart(fig_revenue, use_container_width=True)

with col_right:
    st.subheader("Operating Margin Comparison (2025)")
    fig_margin = px.bar(
        benchmark.sort_values("OPERATING_MARGIN_PCT", ascending=True),
        x="OPERATING_MARGIN_PCT",
        y="COMPANY",
        orientation="h",
        labels={"OPERATING_MARGIN_PCT": "Operating Margin (%)", "COMPANY": "Company"},
        color="OPERATING_MARGIN_PCT",
        color_continuous_scale="Blues"
    )
    fig_margin.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig_margin, use_container_width=True)

# ── Revenue Growth Chart ──────────────────────────────────
st.subheader("Year over Year Revenue Growth (%)")
growth_filtered = growth.dropna(subset=["REVENUE_GROWTH_PCT"])
fig_growth = px.bar(
    growth_filtered,
    x="YEAR",
    y="REVENUE_GROWTH_PCT",
    color="COMPANY",
    barmode="group",
    labels={"REVENUE_GROWTH_PCT": "Revenue Growth (%)", "YEAR": "Year", "COMPANY": "Company"}
)
fig_growth.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3))
st.plotly_chart(fig_growth, use_container_width=True)

# ── Benchmark Table ───────────────────────────────────────
st.subheader("Competitive Benchmark (Latest Year)")
st.dataframe(
    benchmark[[
        "COMPANY", "REVENUE_B", "OPERATING_INCOME_B",
        "NET_INCOME_B", "OPERATING_MARGIN_PCT", "NET_MARGIN_PCT"
    ]].rename(columns={
        "COMPANY":              "Company",
        "REVENUE_B":            "Revenue ($B)",
        "OPERATING_INCOME_B":   "Op. Income ($B)",
        "NET_INCOME_B":         "Net Income ($B)",
        "OPERATING_MARGIN_PCT": "Op. Margin %",
        "NET_MARGIN_PCT":       "Net Margin %"
    }),
    use_container_width=True,
    hide_index=True
)

st.divider()

# ── AI Chat ───────────────────────────────────────────────
st.subheader("💬 Ask the Data")
st.markdown("Ask anything about MedTech financials — revenue, margins, growth trends, competitive comparisons.")
st.caption("Available metrics: Revenue, Operating Income, Net Income, Operating Margin, Net Margin, Revenue Growth | Companies: Medtronic, Boston Scientific, Abbott, Stryker | Years: 2021–2025")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("e.g. Which company had the highest operating margin in 2024?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Querying Snowflake..."):
            try:
                df_result, sql_used = run_nl_query(prompt)
                narrative = generate_narrative(prompt, df_result)

                st.markdown(narrative)
                st.dataframe(df_result, use_container_width=True, hide_index=True)

                with st.expander("View generated SQL"):
                    st.code(sql_used, language="sql")

                full_response = narrative

            except ValueError as e:
                if "metric_not_available" in str(e):
                    full_response = "That metric isn't available in our dataset. I have Revenue, Operating Income, Net Income, Operating Margin, Net Margin, and Revenue Growth for Medtronic, Boston Scientific, Abbott, and Stryker from 2021 to 2025."
                else:
                    full_response = "No data was found for that query. Try asking about revenue, operating margin, net income, or revenue growth for one of the four companies between 2021 and 2025."
                st.warning(full_response)

            except Exception as e:
                full_response = f"Something went wrong: {str(e)}"
                st.error(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

# ── Footer ────────────────────────────────────────────────
st.divider()
st.markdown("*Data sourced from SEC EDGAR public filings. Built with Snowflake, OpenAI GPT-4o, and Streamlit.*")