-- models/final/monthly_kpi.sql
-- KPIs mensuels : évolution 2024→2025 et impact de la CBD congestion fee

SELECT
    pickup_year,
    pickup_month,

    COUNT(*)                                                    AS trip_count,
    ROUND(SUM(total_amount), 2)                                 AS total_revenue,
    ROUND(AVG(fare_amount), 2)                                  AS avg_fare,
    ROUND(AVG(total_amount), 2)                                 AS avg_total_amount,
    ROUND(AVG(tip_rate), 2)                                     AS avg_tip_rate,
    ROUND(AVG(trip_duration_minutes), 2)                        AS avg_duration_minutes,
    ROUND(AVG(trip_distance), 2)                                AS avg_distance_miles,
    ROUND(AVG(total_surcharges), 2)                             AS avg_total_surcharges,
    ROUND(AVG(base_fare_ratio), 2)                              AS avg_base_fare_ratio,

    -- Impact CBD congestion fee (active depuis janvier 2025)
    ROUND(AVG(cbd_congestion_fee), 4)                           AS avg_cbd_congestion_fee,
    ROUND(SUM(cbd_congestion_fee), 2)                           AS total_cbd_congestion_fee,
    SUM(CASE WHEN cbd_congestion_fee > 0 THEN 1 ELSE 0 END)     AS trips_with_cbd_fee,

    -- Répartition par type de trajet
    ROUND(SUM(CASE WHEN is_airport_trip THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                AS pct_airport_trips,
    ROUND(SUM(CASE WHEN is_rush_hour THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                AS pct_rush_hour_trips,
    ROUND(SUM(CASE WHEN is_weekend THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                AS pct_weekend_trips,
    ROUND(SUM(CASE WHEN has_tip THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                AS pct_trips_with_tip

FROM {{ ref('clean_trips') }}
GROUP BY pickup_year, pickup_month
ORDER BY pickup_year, pickup_month
