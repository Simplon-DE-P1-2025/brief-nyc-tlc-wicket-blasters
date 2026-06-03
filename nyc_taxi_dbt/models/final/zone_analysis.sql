-- models/final/zone_analysis.sql
-- Analyse par zone TLC : activité en pickup et en dropoff

WITH pickup_stats AS (
    SELECT
        pulocationid              AS zone_id,
        'pickup'                  AS zone_role,
        COUNT(*)                  AS trip_count,
        ROUND(SUM(total_amount), 2)          AS total_revenue,
        ROUND(AVG(fare_amount), 2)           AS avg_fare,
        ROUND(AVG(tip_rate), 2)              AS avg_tip_rate,
        ROUND(AVG(trip_distance), 2)         AS avg_distance_miles,
        ROUND(AVG(trip_duration_minutes), 2) AS avg_duration_minutes,
        ROUND(SUM(CASE WHEN is_airport_trip THEN 1 ELSE 0 END)
              * 100.0 / COUNT(*), 2)         AS pct_airport_trips,
        ROUND(SUM(CASE WHEN has_tip THEN 1 ELSE 0 END)
              * 100.0 / COUNT(*), 2)         AS pct_trips_with_tip
    FROM {{ ref('clean_trips') }}
    GROUP BY pulocationid
),

dropoff_stats AS (
    SELECT
        dolocationid              AS zone_id,
        'dropoff'                 AS zone_role,
        COUNT(*)                  AS trip_count,
        ROUND(SUM(total_amount), 2)          AS total_revenue,
        ROUND(AVG(fare_amount), 2)           AS avg_fare,
        ROUND(AVG(tip_rate), 2)              AS avg_tip_rate,
        ROUND(AVG(trip_distance), 2)         AS avg_distance_miles,
        ROUND(AVG(trip_duration_minutes), 2) AS avg_duration_minutes,
        ROUND(SUM(CASE WHEN is_airport_trip THEN 1 ELSE 0 END)
              * 100.0 / COUNT(*), 2)         AS pct_airport_trips,
        ROUND(SUM(CASE WHEN has_tip THEN 1 ELSE 0 END)
              * 100.0 / COUNT(*), 2)         AS pct_trips_with_tip
    FROM {{ ref('clean_trips') }}
    GROUP BY dolocationid
)

SELECT * FROM pickup_stats
UNION ALL
SELECT * FROM dropoff_stats
ORDER BY zone_role, trip_count DESC
