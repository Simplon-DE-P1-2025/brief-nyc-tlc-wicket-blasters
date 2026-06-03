-- models/final/vendor_performance.sql
-- Comparaison des 4 fournisseurs TPEP sur qualité de service et revenus

WITH totals AS (
    SELECT COUNT(*) AS total_trips FROM {{ ref('clean_trips') }}
)

SELECT
    t.vendorid,
    t.vendor_name,

    COUNT(*)                                                        AS trip_count,
    ROUND(COUNT(*) * 100.0 / MAX(tot.total_trips), 2)              AS market_share_pct,
    ROUND(SUM(t.total_amount), 2)                                   AS total_revenue,
    ROUND(AVG(t.fare_amount), 2)                                    AS avg_fare,
    ROUND(AVG(t.total_amount), 2)                                   AS avg_total_amount,
    ROUND(AVG(t.tip_rate), 2)                                       AS avg_tip_rate,
    ROUND(AVG(t.avg_speed_mph), 2)                                  AS avg_speed_mph,
    ROUND(AVG(t.trip_duration_minutes), 2)                          AS avg_duration_minutes,
    ROUND(AVG(t.trip_distance), 2)                                  AS avg_distance_miles,
    ROUND(SUM(CASE WHEN t.is_store_and_fwd THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                    AS pct_store_and_fwd,
    ROUND(SUM(CASE WHEN t.has_tip THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                    AS pct_trips_with_tip,
    ROUND(SUM(CASE WHEN t.is_airport_trip THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                    AS pct_airport_trips

FROM {{ ref('clean_trips') }} t
CROSS JOIN totals tot
GROUP BY t.vendorid, t.vendor_name
ORDER BY trip_count DESC
