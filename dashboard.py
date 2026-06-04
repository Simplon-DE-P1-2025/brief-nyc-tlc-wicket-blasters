import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────
# CONNEXION
# ──────────────────────────────────────────────────────────────

def get_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "NYC_TAXI_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "NYC_TAXI_DB"),
        role=os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
        schema="FINAL",
    )

@st.cache_data(ttl=36000, show_spinner="Chargement des données...")
def query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        df = cur.fetch_pandas_all()
        df.columns = df.columns.str.lower()
        return df
    finally:
        conn.close()

MONTH_NAMES = {1:"Jan",2:"Fév",3:"Mar",4:"Avr",5:"Mai",6:"Jun",
               7:"Jul",8:"Aoû",9:"Sep",10:"Oct",11:"Nov",12:"Déc"}
MONTH_ORDER = list(MONTH_NAMES.values())

# ──────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="NYC Yellow Taxi", page_icon="🚕", layout="wide")
st.title("🚕 NYC Yellow Taxi — Analyse 2024-2025")

section = st.sidebar.radio("Navigation", [
    "🏠 Accueil",
    "📅 Daily Summary",
    "🗺️ Zone Analysis",
    "🕐 Hourly Patterns",
    "🏢 Vendor Performance",
    "💳 Payment Analysis",
    "📈 Monthly KPI",
])

# ──────────────────────────────────────────────────────────────
# ACCUEIL
# ──────────────────────────────────────────────────────────────

if section == "🏠 Accueil":

    df_kpi = query("""
        SELECT SUM(trip_count)                    AS total_trips,
               ROUND(SUM(total_revenue), 0)       AS total_revenue,
               ROUND(AVG(avg_fare), 2)            AS avg_fare,
               ROUND(AVG(avg_tip_rate), 2)        AS avg_tip_rate,
               ROUND(AVG(avg_duration_minutes), 2) AS avg_duration
        FROM NYC_TAXI_DB.FINAL.DAILY_SUMMARY
    """)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🚕 Total trajets",  f"{int(df_kpi['total_trips'][0]):,}")
    c2.metric("💰 Revenus totaux", f"${int(df_kpi['total_revenue'][0]):,}")
    c3.metric("🏷️ Tarif moyen",    f"${df_kpi['avg_fare'][0]:.2f}")
    c4.metric("💸 Tip rate moyen", f"{df_kpi['avg_tip_rate'][0]:.1f}%")
    c5.metric("⏱️ Durée moyenne",  f"{df_kpi['avg_duration'][0]:.0f} min")

    st.divider()
    st.subheader("Activité mensuelle")
    df_m = query("""
        SELECT pickup_year, pickup_month,
               SUM(trip_count)              AS monthly_trips,
               ROUND(SUM(total_revenue), 0) AS monthly_revenue
        FROM NYC_TAXI_DB.FINAL.DAILY_SUMMARY
        GROUP BY pickup_year, pickup_month ORDER BY pickup_year, pickup_month
    """)
    df_m["period"] = df_m["pickup_year"].astype(str) + "-" + df_m["pickup_month"].astype(str).str.zfill(2)
    df_m["pickup_year"] = df_m["pickup_year"].astype(str)
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df_m, x="period", y="monthly_trips", color="pickup_year",
                     title="Volume mensuel", color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        df_m["mois"] = df_m["pickup_month"].map(MONTH_NAMES) if "pickup_month" in df_m.columns else df_m["period"]
        fig = px.line(df_m, x="period", y="monthly_revenue", color="pickup_year",
                      title="Revenus mensuels ($)", markers=True,
                      color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Zones & Patterns")
    col1, col2 = st.columns(2)
    with col1:
        df_z = query("""
            SELECT zone_name, borough, trip_count, avg_fare
            FROM NYC_TAXI_DB.FINAL.ZONE_ANALYSIS
            WHERE zone_role = 'pickup' ORDER BY trip_count DESC LIMIT 10
        """)
        df_z["label"] = df_z["zone_name"] + " (" + df_z["borough"] + ")"
        fig = px.bar(df_z, x="trip_count", y="label", orientation="h",
                     color="avg_fare", color_continuous_scale="Viridis",
                     title="Top 10 zones pickup")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        df_h = query("""
            SELECT pickup_weekday, pickup_hour, SUM(trip_count) AS total_trips
            FROM NYC_TAXI_DB.FINAL.HOURLY_PATTERNS
            GROUP BY pickup_weekday, pickup_hour
        """)
        order = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        piv = df_h.pivot(index="pickup_weekday", columns="pickup_hour", values="total_trips")
        piv = piv.reindex([d for d in order if d in piv.index])
        fig = px.imshow(piv, aspect="auto", color_continuous_scale="YlOrRd",
                        title="Heatmap heure × jour",
                        labels={"x":"Heure","y":"Jour","color":"Trajets"})
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Fournisseurs & Paiements")
    col1, col2 = st.columns(2)
    with col1:
        df_v = query("SELECT vendor_name, trip_count FROM NYC_TAXI_DB.FINAL.VENDOR_PERFORMANCE ORDER BY trip_count DESC")
        fig = px.pie(df_v, names="vendor_name", values="trip_count",
                     title="Parts de marché fournisseurs", hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        df_p = query("""
            SELECT payment_type_label, SUM(trip_count) AS total_trips
            FROM NYC_TAXI_DB.FINAL.PAYMENT_ANALYSIS
            GROUP BY payment_type_label ORDER BY total_trips DESC
        """)
        fig = px.pie(df_p, names="payment_type_label", values="total_trips",
                     title="Distribution des paiements", hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# DAILY SUMMARY
# ──────────────────────────────────────────────────────────────

elif section == "📅 Daily Summary":
    st.header("📅 Daily Summary")

    df = query("""
        SELECT pickup_year, pickup_month,
               SUM(trip_count)              AS monthly_trips,
               ROUND(SUM(total_revenue), 2) AS monthly_revenue,
               ROUND(AVG(avg_fare), 2)       AS avg_daily_fare,
               ROUND(AVG(avg_tip_rate), 2)   AS avg_tip_rate
        FROM NYC_TAXI_DB.FINAL.DAILY_SUMMARY
        GROUP BY pickup_year, pickup_month ORDER BY pickup_year, pickup_month
    """)
    df["period"] = df["pickup_year"].astype(str) + "-" + df["pickup_month"].astype(str).str.zfill(2)
    df["mois"]   = df["pickup_month"].map(MONTH_NAMES)
    df["pickup_year"] = df["pickup_year"].astype(str)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df, x="period", y="monthly_trips", color="pickup_year",
                     title="Volume mensuel de trajets",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.line(df, x="mois", y="monthly_revenue", color="pickup_year",
                      title="Revenus mensuels ($) — 2024 vs 2025", markers=True,
                      color_discrete_sequence=px.colors.qualitative.Set2,
                      category_orders={"mois": MONTH_ORDER})
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(df, x="mois", y="avg_daily_fare", color="pickup_year",
                      title="Tarif moyen mensuel ($) — 2024 vs 2025", markers=True,
                      color_discrete_sequence=px.colors.qualitative.Set2,
                      category_orders={"mois": MONTH_ORDER})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.line(df, x="mois", y="avg_tip_rate", color="pickup_year",
                      title="Tip rate moyen (%) — 2024 vs 2025", markers=True,
                      color_discrete_sequence=px.colors.qualitative.Set2,
                      category_orders={"mois": MONTH_ORDER})
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top journées")
    col1, col2 = st.columns(2)
    with col1:
        df_vol = query("""
            SELECT pickup_date, trip_count, total_revenue
            FROM NYC_TAXI_DB.FINAL.DAILY_SUMMARY ORDER BY trip_count DESC LIMIT 10
        """)
        fig = px.bar(df_vol, x="pickup_date", y="trip_count",
                     color="total_revenue", color_continuous_scale="Blues",
                     title="Top 10 journées (volume)")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        df_rev = query("""
            SELECT pickup_date, total_revenue,
                   ROUND(total_revenue / trip_count, 2) AS revenue_per_trip
            FROM NYC_TAXI_DB.FINAL.DAILY_SUMMARY ORDER BY total_revenue DESC LIMIT 10
        """)
        fig = px.bar(df_rev, x="pickup_date", y="total_revenue",
                     color="revenue_per_trip", color_continuous_scale="Greens",
                     title="Top 10 journées (revenus)")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Weekend vs Semaine")
    df_wk = query("""
        SELECT is_weekend,
               SUM(trip_count)                     AS total_trips,
               ROUND(AVG(avg_fare), 2)             AS avg_fare,
               ROUND(AVG(avg_tip_rate), 2)         AS avg_tip_rate,
               ROUND(AVG(avg_duration_minutes), 2) AS avg_duration,
               ROUND(AVG(avg_speed_mph), 2)        AS avg_speed
        FROM NYC_TAXI_DB.FINAL.DAILY_SUMMARY GROUP BY is_weekend
    """)
    df_wk["journee"] = df_wk["is_weekend"].apply(lambda x: "Weekend" if x else "Semaine")
    col1, col2, col3 = st.columns(3)
    with col1:
        fig = px.pie(df_wk, names="journee", values="total_trips",
                     title="Volume", color_discrete_sequence=px.colors.qualitative.Pastel, hole=0.4)
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df_wk.melt(id_vars="journee", value_vars=["avg_fare", "avg_tip_rate"]),
                     x="journee", y="value", color="variable",
                     barmode="group", title="Tarif ($) et Tip rate (%)")
        st.plotly_chart(fig, use_container_width=True)
    with col3:
        fig = px.bar(df_wk.melt(id_vars="journee", value_vars=["avg_duration", "avg_speed"]),
                     x="journee", y="value", color="variable",
                     barmode="group", title="Durée (min) et Vitesse (mph)")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Part des trajets aéroport")
    df_ap = query("""
        SELECT pickup_year, pickup_month,
               ROUND(AVG(pct_airport_trips), 2) AS avg_pct_airport
        FROM NYC_TAXI_DB.FINAL.DAILY_SUMMARY
        GROUP BY pickup_year, pickup_month ORDER BY pickup_year, pickup_month
    """)
    df_ap["mois"] = df_ap["pickup_month"].map(MONTH_NAMES)
    df_ap["pickup_year"] = df_ap["pickup_year"].astype(str)
    df_pivot = df_ap.pivot(index="mois", columns="pickup_year", values="avg_pct_airport")
    df_pivot = df_pivot.reindex(MONTH_ORDER).reset_index().rename(columns={"mois": "Mois"})
    df_pivot.columns = ["Mois"] + [f"% aéroport {c}" for c in df_pivot.columns[1:]]
    st.dataframe(df_pivot, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────────────────────
# ZONE ANALYSIS
# ──────────────────────────────────────────────────────────────

elif section == "🗺️ Zone Analysis":
    st.header("🗺️ Zone Analysis")

    n = st.slider("Nombre de zones à afficher", 10, 30, 15)

    col1, col2 = st.columns(2)
    with col1:
        df = query(f"""
            SELECT zone_name, borough, trip_count, avg_fare, avg_tip_rate
            FROM NYC_TAXI_DB.FINAL.ZONE_ANALYSIS
            WHERE zone_role = 'pickup' ORDER BY trip_count DESC LIMIT {n}
        """)
        df["label"] = df["zone_name"] + " (" + df["borough"] + ")"
        fig = px.bar(df, x="trip_count", y="label", orientation="h",
                     color="avg_fare", color_continuous_scale="Viridis",
                     title=f"Top {n} zones de pickup")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        df = query(f"""
            SELECT zone_name, borough, trip_count, avg_fare
            FROM NYC_TAXI_DB.FINAL.ZONE_ANALYSIS
            WHERE zone_role = 'dropoff' ORDER BY trip_count DESC LIMIT {n}
        """)
        df["label"] = df["zone_name"] + " (" + df["borough"] + ")"
        fig = px.bar(df, x="trip_count", y="label", orientation="h",
                     color="avg_fare", color_continuous_scale="Plasma",
                     title=f"Top {n} zones de dropoff")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Volume vs Tarif moyen")
    min_trips = st.number_input("Volume minimum de trajets", 100, 10000, 1000, step=100)
    df_sc = query(f"""
        SELECT zone_name, borough, avg_fare, avg_tip_rate, trip_count, pct_trips_with_tip
        FROM NYC_TAXI_DB.FINAL.ZONE_ANALYSIS
        WHERE zone_role = 'pickup' AND trip_count >= {min_trips}
        ORDER BY avg_fare DESC LIMIT 20
    """)
    fig = px.scatter(df_sc, x="trip_count", y="avg_fare",
                     size="avg_tip_rate", color="avg_tip_rate",
                     hover_data=["zone_name", "borough"],
                     title="Volume vs Tarif moyen par zone",
                     color_continuous_scale="RdYlGn")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Déséquilibre Pickup vs Dropoff")
    df_imb = query("""
        SELECT p.zone_name, p.borough,
               p.trip_count AS pickup_count,
               d.trip_count AS dropoff_count,
               d.trip_count - p.trip_count AS dropoff_surplus
        FROM NYC_TAXI_DB.FINAL.ZONE_ANALYSIS p
        JOIN NYC_TAXI_DB.FINAL.ZONE_ANALYSIS d
            ON p.zone_id = d.zone_id AND d.zone_role = 'dropoff'
        WHERE p.zone_role = 'pickup'
        ORDER BY ABS(d.trip_count - p.trip_count) DESC LIMIT 20
    """)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Pickup",  x=df_imb["zone_name"], y=df_imb["pickup_count"],  marker_color="#636EFA"))
    fig.add_trace(go.Bar(name="Dropoff", x=df_imb["zone_name"], y=df_imb["dropoff_count"], marker_color="#EF553B"))
    fig.update_layout(barmode="group", title="Déséquilibre Pickup vs Dropoff par zone", xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_imb, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────────────────────
# HOURLY PATTERNS
# ──────────────────────────────────────────────────────────────

elif section == "🕐 Hourly Patterns":
    st.header("🕐 Hourly Patterns")

    col1, col2 = st.columns(2)
    with col1:
        df_h = query("""
            SELECT pickup_weekday, pickup_hour, SUM(trip_count) AS total_trips
            FROM NYC_TAXI_DB.FINAL.HOURLY_PATTERNS
            GROUP BY pickup_weekday, pickup_hour
        """)
        order = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        piv = df_h.pivot(index="pickup_weekday", columns="pickup_hour", values="total_trips")
        piv = piv.reindex([d for d in order if d in piv.index])
        fig = px.imshow(piv, aspect="auto", color_continuous_scale="YlOrRd",
                        title="Heatmap : volume par heure et jour",
                        labels={"x":"Heure","y":"Jour","color":"Trajets"})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        df_hr = query("""
            SELECT pickup_hour, SUM(trip_count) AS total_trips,
                   ROUND(AVG(avg_fare), 2) AS avg_fare,
                   ROUND(AVG(avg_speed_mph), 2) AS avg_speed
            FROM NYC_TAXI_DB.FINAL.HOURLY_PATTERNS
            GROUP BY pickup_hour ORDER BY pickup_hour
        """)
        fig = px.line(df_hr, x="pickup_hour", y="total_trips",
                      title="Volume par heure (toute la semaine)", markers=True)
        fig.update_layout(xaxis_title="Heure")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Rush Hour vs Hors Pointe")
    df_rh = query("""
        SELECT is_rush_hour,
               SUM(trip_count)                     AS total_trips,
               ROUND(AVG(avg_fare), 2)             AS avg_fare,
               ROUND(AVG(avg_duration_minutes), 2) AS avg_duration,
               ROUND(AVG(avg_speed_mph), 2)        AS avg_speed,
               ROUND(AVG(avg_tip_rate), 2)         AS avg_tip_rate
        FROM NYC_TAXI_DB.FINAL.HOURLY_PATTERNS GROUP BY is_rush_hour
    """)
    df_rh["periode"] = df_rh["is_rush_hour"].apply(lambda x: "Rush Hour" if x else "Hors Pointe")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(df_rh, names="periode", values="total_trips",
                     title="Volume Rush Hour vs Hors Pointe",
                     color_discrete_sequence=["#EF553B","#636EFA"], hole=0.4)
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df_rh.melt(id_vars="periode", value_vars=["avg_fare","avg_duration","avg_speed","avg_tip_rate"]),
                     x="variable", y="value", color="periode",
                     barmode="group", title="Métriques Rush Hour vs Hors Pointe",
                     color_discrete_sequence=["#EF553B","#636EFA"])
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Périodes de la journée")
    df_p = query("""
        SELECT time_period, SUM(trip_count) AS total_trips,
               ROUND(AVG(avg_fare), 2) AS avg_fare,
               ROUND(AVG(avg_tip_rate), 2) AS avg_tip_rate,
               ROUND(AVG(avg_speed_mph), 2) AS avg_speed
        FROM NYC_TAXI_DB.FINAL.HOURLY_PATTERNS
        GROUP BY time_period ORDER BY total_trips DESC
    """)
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(df_p, names="time_period", values="total_trips",
                     title="Répartition par période",
                     color_discrete_sequence=px.colors.qualitative.Set3, hole=0.4)
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df_p.melt(id_vars="time_period", value_vars=["avg_fare","avg_tip_rate"]),
                     x="time_period", y="value", color="variable",
                     barmode="group", title="Tarif ($) et Tip rate (%) par période",
                     color_discrete_sequence=["#636EFA","#00CC96"])
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Meilleurs créneaux pour les pourboires")
    df_t = query("""
        SELECT pickup_weekday, pickup_hour,
               ROUND(AVG(avg_tip_rate), 2) AS avg_tip_rate,
               SUM(trip_count) AS trip_count
        FROM NYC_TAXI_DB.FINAL.HOURLY_PATTERNS
        GROUP BY pickup_weekday, pickup_hour
        ORDER BY avg_tip_rate DESC LIMIT 15
    """)
    df_t["creneau"] = df_t["pickup_weekday"] + " " + df_t["pickup_hour"].astype(str) + "h"
    fig = px.bar(df_t, x="creneau", y="avg_tip_rate", color="trip_count",
                 title="Top 15 créneaux avec le meilleur tip rate",
                 color_continuous_scale="Greens")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# VENDOR PERFORMANCE
# ──────────────────────────────────────────────────────────────

elif section == "🏢 Vendor Performance":
    st.header("🏢 Vendor Performance")

    df = query("""
        SELECT vendor_name, trip_count, market_share_pct, total_revenue,
               avg_fare, avg_tip_rate, avg_speed_mph, avg_duration_minutes,
               pct_store_and_fwd, pct_trips_with_tip, pct_airport_trips
        FROM NYC_TAXI_DB.FINAL.VENDOR_PERFORMANCE ORDER BY trip_count DESC
    """)

    cols = st.columns(len(df))
    for i, row in df.iterrows():
        with cols[i]:
            st.metric(row["vendor_name"], f"{row['market_share_pct']}%", f"{int(row['trip_count']):,} trajets")

    st.subheader("Parts de marché & Revenus")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(df, names="vendor_name", values="trip_count",
                     title="Parts de marché (volume)",
                     color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4)
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df, x="vendor_name", y="total_revenue",
                     color="avg_fare", color_continuous_scale="Blues",
                     title="Revenu total ($)")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Qualité de service")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df.melt(id_vars="vendor_name", value_vars=["avg_speed_mph","avg_duration_minutes"]),
                     x="vendor_name", y="value", color="variable",
                     barmode="group", title="Vitesse (mph) vs Durée (min)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df.melt(id_vars="vendor_name", value_vars=["avg_fare","avg_tip_rate","pct_trips_with_tip"]),
                     x="vendor_name", y="value", color="variable",
                     barmode="group", title="Tarif ($), Tip rate (%), % avec tip")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Aéroport & Store-and-Forward")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df, x="vendor_name", y="pct_airport_trips",
                     color="pct_airport_trips", color_continuous_scale="YlOrRd",
                     title="% trajets aéroport")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df, x="vendor_name", y="pct_store_and_fwd",
                     color="pct_store_and_fwd", color_continuous_scale="Purples",
                     title="% trajets store-and-forward")
        st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# PAYMENT ANALYSIS
# ──────────────────────────────────────────────────────────────

elif section == "💳 Payment Analysis":
    st.header("💳 Payment Analysis")

    df = query("""
        SELECT payment_type_label,
               SUM(trip_count)                                                  AS total_trips,
               ROUND(SUM(trip_count)*100.0/SUM(SUM(trip_count)) OVER (), 2)    AS pct_total,
               ROUND(AVG(avg_fare), 2)                                          AS avg_fare,
               ROUND(AVG(avg_tip_rate), 2)                                      AS avg_tip_rate,
               ROUND(AVG(pct_trips_with_tip), 2)                                AS avg_pct_with_tip
        FROM NYC_TAXI_DB.FINAL.PAYMENT_ANALYSIS
        GROUP BY payment_type_label ORDER BY total_trips DESC
    """)

    st.subheader("Distribution globale")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(df, names="payment_type_label", values="total_trips",
                     title="Distribution des modes de paiement",
                     color_discrete_sequence=px.colors.qualitative.Set3, hole=0.4)
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df, x="payment_type_label", y=["avg_fare", "avg_tip_rate"],
                     barmode="group", title="Tarif moyen ($) et Tip rate (%)",
                     color_discrete_sequence=["#636EFA","#00CC96"])
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("Évolution mensuelle")
    df_evo = query("""
        SELECT pickup_year, pickup_month, payment_type_label,
               trip_count, pct_of_monthly_trips, avg_tip_rate
        FROM NYC_TAXI_DB.FINAL.PAYMENT_ANALYSIS
        WHERE payment_type_label IN ('Credit Card', 'Cash', 'Flex Fare')
        ORDER BY pickup_year, pickup_month
    """)
    df_evo["period"] = df_evo["pickup_year"].astype(str) + "-" + df_evo["pickup_month"].astype(str).str.zfill(2)
    fig = px.line(df_evo, x="period", y="pct_of_monthly_trips",
                  color="payment_type_label", markers=True,
                  title="Part mensuelle par mode de paiement (%)",
                  color_discrete_sequence=px.colors.qualitative.Set1)
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tip rate par mode")
    df_tip = query("""
        SELECT payment_type_label,
               ROUND(AVG(avg_tip_rate), 2)       AS avg_tip_rate,
               ROUND(AVG(avg_tip_amount), 2)     AS avg_tip_amount,
               ROUND(AVG(pct_trips_with_tip), 2) AS pct_with_tip
        FROM NYC_TAXI_DB.FINAL.PAYMENT_ANALYSIS
        GROUP BY payment_type_label ORDER BY avg_tip_rate DESC
    """)
    fig = px.bar(df_tip.melt(id_vars="payment_type_label", value_vars=["avg_tip_rate","pct_with_tip"]),
                 x="payment_type_label", y="value", color="variable",
                 barmode="group", title="Tip rate moyen (%) et % trajets avec tip",
                 color_discrete_sequence=["#00CC96","#AB63FA"])
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_tip, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────────────────────
# MONTHLY KPI
# ──────────────────────────────────────────────────────────────

elif section == "📈 Monthly KPI":
    st.header("📈 Monthly KPI — Évolution 2024-2025")

    df = query("""
        SELECT pickup_year, pickup_month, trip_count, total_revenue,
               avg_fare, avg_tip_rate, avg_total_surcharges, avg_base_fare_ratio,
               avg_cbd_congestion_fee, total_cbd_congestion_fee, trips_with_cbd_fee,
               pct_airport_trips, pct_rush_hour_trips, pct_weekend_trips, pct_trips_with_tip
        FROM NYC_TAXI_DB.FINAL.MONTHLY_KPI ORDER BY pickup_year, pickup_month
    """)
    df["mois"] = df["pickup_month"].map(MONTH_NAMES)
    df["pickup_year"] = df["pickup_year"].astype(str)
    df["pct_cbd"] = (df["trips_with_cbd_fee"] / df["trip_count"] * 100).round(2)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total trajets",   f"{df['trip_count'].sum():,.0f}")
    col2.metric("Revenus totaux",  f"${df['total_revenue'].sum():,.0f}")
    col3.metric("Tarif moyen",     f"${df['avg_fare'].mean():.2f}")

    st.subheader("Vue d'ensemble")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(df, x="mois", y="trip_count", color="pickup_year",
                      title="Volume mensuel", markers=True,
                      color_discrete_sequence=px.colors.qualitative.Set2,
                      category_orders={"mois": MONTH_ORDER})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.line(df, x="mois", y="avg_fare", color="pickup_year",
                      title="Tarif moyen ($)", markers=True,
                      color_discrete_sequence=px.colors.qualitative.Set2,
                      category_orders={"mois": MONTH_ORDER})
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Impact CBD Congestion Fee")
    st.info("Péage de congestion MTA actif depuis le 5 janvier 2025 pour les trajets entrant dans la Congestion Relief Zone.")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df, x="mois", y="total_cbd_congestion_fee", color="pickup_year",
                     title="Revenus CBD Congestion Fee ($)",
                     color_discrete_sequence=["#636EFA","#EF553B"],
                     category_orders={"mois": MONTH_ORDER})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df, x="mois", y="pct_cbd", color="pickup_year",
                     title="% trajets avec CBD Congestion Fee",
                     color_discrete_sequence=["#636EFA","#EF553B"],
                     category_orders={"mois": MONTH_ORDER})
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Comparaison 2024 vs 2025")
    df24 = df[df["pickup_year"]=="2024"][["pickup_month","trip_count","avg_fare"]].rename(
        columns={"trip_count":"trips_2024","avg_fare":"fare_2024"})
    df25 = df[df["pickup_year"]=="2025"][["pickup_month","trip_count","avg_fare"]].rename(
        columns={"trip_count":"trips_2025","avg_fare":"fare_2025"})
    df_cmp = df24.merge(df25, on="pickup_month", how="inner")
    df_cmp["growth_pct"] = ((df_cmp["trips_2025"]-df_cmp["trips_2024"])/df_cmp["trips_2024"]*100).round(2)
    df_cmp["mois"] = df_cmp["pickup_month"].map(MONTH_NAMES)
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="2024", x=df_cmp["mois"], y=df_cmp["trips_2024"], marker_color="#636EFA"))
        fig.add_trace(go.Bar(name="2025", x=df_cmp["mois"], y=df_cmp["trips_2025"], marker_color="#EF553B"))
        fig.update_layout(barmode="group", title="Volume mensuel 2024 vs 2025")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df_cmp, x="mois", y="growth_pct",
                     title="Croissance 2024→2025 (%)",
                     color="growth_pct", color_continuous_scale="RdYlGn")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Indicateurs clés")
    fig = px.line(df, x="mois",
                  y=["pct_airport_trips","pct_rush_hour_trips","pct_weekend_trips","pct_trips_with_tip"],
                  title="Évolution des indicateurs (%)", markers=True,
                  color_discrete_sequence=px.colors.qualitative.Set1)
    st.plotly_chart(fig, use_container_width=True)
