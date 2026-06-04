import streamlit as st
import pandas as pd

# -------------------------------------------------------------
# Connexion
# Streamlit in Snowflake : session native, aucune config requise
# Local : remplacer le bloc ci-dessous par :
#   import snowflake.connector, os
#   conn = snowflake.connector.connect(
#       account=os.getenv("SNOWFLAKE_ACCOUNT"), user=os.getenv("SNOWFLAKE_USER"),
#       password=os.getenv("SNOWFLAKE_PASSWORD"), warehouse="NYC_TAXI_WH",
#       database="NYC_TAXI_DB", role="SYSADMIN"
#   )
#   def query(sql): return pd.read_sql(sql, conn)
# -------------------------------------------------------------
from snowflake.snowpark.context import get_active_session
session = get_active_session()

def query(sql):
    return session.sql(sql).to_pandas()

# -------------------------------------------------------------
# Page
# -------------------------------------------------------------
st.set_page_config(page_title="NYC Taxi — Pipeline Monitor", layout="wide")
st.title("NYC Taxi Pipeline — Monitoring")

# -------------------------------------------------------------
# Section 1 : Statut de l'ingestion RAW
# -------------------------------------------------------------
st.header("Ingestion RAW")

df_raw = query("""
    SELECT
        MAX(_loaded_at)           AS derniere_ingestion,
        COUNT(DISTINCT _source_file) AS fichiers_charges,
        COUNT(*)                  AS total_lignes
    FROM NYC_TAXI_DB.RAW.YELLOW_TAXI_TRIPS
""")

col1, col2, col3 = st.columns(3)
col1.metric("Dernière ingestion",   str(df_raw["DERNIERE_INGESTION"][0])[:16])
col2.metric("Fichiers chargés",     int(df_raw["FICHIERS_CHARGES"][0]))
col3.metric("Lignes brutes (RAW)",  f"{int(df_raw['TOTAL_LIGNES'][0]):,}")

# -------------------------------------------------------------
# Section 2 : Taux de rétention RAW → STAGING
# -------------------------------------------------------------
st.header("Qualité — RAW vs STAGING")

df_staging = query("""
    SELECT COUNT(*) AS total_lignes
    FROM NYC_TAXI_DB.STAGING.CLEAN_TRIPS
""")

raw_count     = int(df_raw["TOTAL_LIGNES"][0])
staging_count = int(df_staging["TOTAL_LIGNES"][0])
rejets        = raw_count - staging_count
taux          = round(staging_count / raw_count * 100, 1) if raw_count > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Lignes STAGING (clean_trips)", f"{staging_count:,}")
col2.metric("Lignes rejetées",              f"{rejets:,}")
col3.metric("Taux de rétention",            f"{taux} %")

# -------------------------------------------------------------
# Section 3 : Détail par fichier source
# -------------------------------------------------------------
st.header("Détail par fichier source")

df_files = query("""
    SELECT
        _source_file                    AS fichier,
        MIN(_loaded_at)                 AS charge_le,
        COUNT(*)                        AS nb_lignes
    FROM NYC_TAXI_DB.RAW.YELLOW_TAXI_TRIPS
    GROUP BY _source_file
    ORDER BY _source_file
""")

df_chart = df_files.copy()
df_chart["LABEL"] = df_chart["FICHIER"].str.extract(r'(\d{4}-\d{2})')[0].fillna(df_chart["FICHIER"].str.slice(-10))
st.bar_chart(df_chart.set_index("LABEL")["NB_LIGNES"])
st.dataframe(df_files, use_container_width=True)

# -------------------------------------------------------------
# Section 4 : État des tables FINAL
# -------------------------------------------------------------
st.header("Tables FINAL")

final_tables = [
    "DAILY_SUMMARY",
    "HOURLY_PATTERNS",
    "MONTHLY_KPI",
    "PAYMENT_ANALYSIS",
    "VENDOR_PERFORMANCE",
    "ZONE_ANALYSIS",
]

cols = st.columns(len(final_tables))
for i, table in enumerate(final_tables):
    try:
        df = query(f"SELECT COUNT(*) AS n FROM NYC_TAXI_DB.FINAL.{table}")
        cols[i].metric(table.replace("_", " ").title(), f"{int(df['N'][0]):,}")
    except Exception:
        cols[i].metric(table.replace("_", " ").title(), "N/A")
