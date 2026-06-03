-- models/final/payment_analysis.sql
-- Distribution des modes de paiement et comportement de pourboire

WITH totals AS (
    SELECT
        pickup_year,
        pickup_month,
        COUNT(*) AS monthly_trips
    FROM {{ ref('clean_trips') }}
    GROUP BY pickup_year, pickup_month
)

SELECT
    t.pickup_year,
    t.pickup_month,
    t.payment_type,
    t.payment_type_label,

    COUNT(*)                                                        AS trip_count,
    ROUND(COUNT(*) * 100.0 / MAX(tot.monthly_trips), 2)            AS pct_of_monthly_trips,
    ROUND(AVG(t.fare_amount), 2)                                    AS avg_fare,
    ROUND(AVG(t.tip_amount), 2)                                     AS avg_tip_amount,
    ROUND(AVG(t.tip_rate), 2)                                       AS avg_tip_rate,
    ROUND(SUM(CASE WHEN t.has_tip THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                    AS pct_trips_with_tip,
    ROUND(AVG(t.total_amount), 2)                                   AS avg_total_amount

FROM {{ ref('clean_trips') }} t
JOIN totals tot
    ON t.pickup_year = tot.pickup_year
    AND t.pickup_month = tot.pickup_month
GROUP BY
    t.pickup_year, t.pickup_month, t.payment_type, t.payment_type_label
ORDER BY
    t.pickup_year, t.pickup_month, trip_count DESC
