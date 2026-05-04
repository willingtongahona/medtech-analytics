# MedTech Financial Intelligence Tool

An end-to-end financial reporting pipeline built to analyze and benchmark 
Medtronic, Boston Scientific, Abbott, and Stryker using public SEC EDGAR filings.

## Live Demo

[medtech-analytics.streamlit.app](https://medtech-analytics.streamlit.app)  
Password: REQUEST OWNER

## What It Does

- Pulls annual financial data (Revenue, Operating Income, Net Income) for 4 
  MedTech companies directly from the SEC EDGAR API
- Loads and transforms the data in a Snowflake data warehouse using raw and 
  transformed schema layers
- Surfaces key metrics through an interactive Streamlit dashboard with Plotly 
  visualizations
- Includes an OpenAI GPT-4o powered natural language query interface that 
  converts plain English questions into Snowflake SQL and generates 3-sentence 
  variance narratives automatically

## Architecture

SEC EDGAR API → Python Pipeline → Snowflake (Raw + Transformed) → Streamlit + Plotly + OpenAI

## Tech Stack

- Python for data ingestion and pipeline orchestration
- SEC EDGAR Company Facts API for public financial data
- Snowflake as the cloud data warehouse
- SQL views for the transformed reporting layer
- OpenAI GPT-4o for natural language to SQL conversion and narrative generation
- Streamlit and Plotly for the interactive dashboard and deployment
- Streamlit Cloud for hosting

## Data

All data sourced from SEC EDGAR public filings. Covers fiscal years 2021 to 2025 
for the following companies:

| Ticker | Company |
|--------|---------|
| MDT | Medtronic |
| BSX | Boston Scientific |
| ABT | Abbott |
| SYK | Stryker |

## Metrics Available

- Revenue ($B)
- Operating Income ($B)
- Net Income ($B)
- Operating Margin (%)
- Net Margin (%)
- Year over Year Revenue Growth (%)

## Why I Built This

This project was built to demonstrate end-to-end financial systems and analytics 
skills relevant to financial reporting and analytics roles in the MedTech industry. 
The architecture mirrors how enterprise reporting pipelines connect data sources to 
warehouses to visualization layers, with an AI layer for automated narrative generation.

## Author

Willington Gahona-Perez  
Financial Analyst | MSBA Candidate, UT Austin McCombs
