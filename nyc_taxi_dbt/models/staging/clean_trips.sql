-- models/staging/clean_trips.sql
-- ============================================================
-- STAGING : Nettoyage et enrichissement des données brutes
-- Source : NYC TLC Yellow Taxi Trip Records
-- ============================================================

WITH source AS (
    SELECT * FROM {{ source('raw', 'yellow_taxi_trips') }}
),

cleaned AS (
    SELECT

        -- --------------------------------------------------------
        -- Identifiants & labels fournisseur
        -- --------------------------------------------------------
        VendorID,

        CASE VendorID
            WHEN 1 THEN 'Creative Mobile Technologies'
            WHEN 2 THEN 'Curb Mobility'
            WHEN 6 THEN 'Myle Technologies'
            WHEN 7 THEN 'Helix'
        END AS vendor_name,

        -- --------------------------------------------------------
        -- Horodatages
        -- --------------------------------------------------------
        tpep_pickup_datetime  AS pickup_datetime,
        tpep_dropoff_datetime AS dropoff_datetime,
        CAST(tpep_pickup_datetime AS DATE) AS pickup_date,

        -- --------------------------------------------------------
        -- Dimensions temporelles
        -- --------------------------------------------------------
        YEAR(tpep_pickup_datetime)    AS pickup_year,
        MONTH(tpep_pickup_datetime)   AS pickup_month,
        DAY(tpep_pickup_datetime)     AS pickup_day,
        HOUR(tpep_pickup_datetime)    AS pickup_hour,
        DAYNAME(tpep_pickup_datetime) AS pickup_weekday,

        CASE
            WHEN HOUR(tpep_pickup_datetime) BETWEEN 6  AND 11 THEN 'Morning'
            WHEN HOUR(tpep_pickup_datetime) BETWEEN 12 AND 17 THEN 'Afternoon'
            WHEN HOUR(tpep_pickup_datetime) BETWEEN 18 AND 22 THEN 'Evening'
            ELSE 'Night'
        END AS time_period,

        DAYNAME(tpep_pickup_datetime) IN ('Sat', 'Sun') AS is_weekend,

        -- Heures de pointe NYC : lundi-vendredi, 7h-9h et 16h-19h
        (
            DAYOFWEEK(tpep_pickup_datetime) BETWEEN 2 AND 6
            AND (
                HOUR(tpep_pickup_datetime) BETWEEN 7 AND 8
                OR HOUR(tpep_pickup_datetime) BETWEEN 16 AND 18
            )
        ) AS is_rush_hour,

        -- --------------------------------------------------------
        -- Métriques de trajet
        -- --------------------------------------------------------
        passenger_count,
        trip_distance,

        ROUND(
            DATEDIFF('minute', tpep_pickup_datetime, tpep_dropoff_datetime),
            2
        ) AS trip_duration_minutes,

        CASE
            WHEN DATEDIFF('minute', tpep_pickup_datetime, tpep_dropoff_datetime) > 0
            THEN ROUND(
                trip_distance / (
                    DATEDIFF('minute', tpep_pickup_datetime, tpep_dropoff_datetime) / 60
                ),
                2
            )
            ELSE NULL
        END AS avg_speed_mph,

        CASE
            WHEN trip_distance < 1  THEN 'Short'
            WHEN trip_distance < 5  THEN 'Medium'
            WHEN trip_distance < 20 THEN 'Long'
            ELSE 'Very Long'
        END AS distance_category,

        -- --------------------------------------------------------
        -- Localisation & tarification
        -- --------------------------------------------------------
        RatecodeID,

        CASE RatecodeID
            WHEN 1  THEN 'Standard Rate'
            WHEN 2  THEN 'JFK'
            WHEN 3  THEN 'Newark'
            WHEN 4  THEN 'Nassau/Westchester'
            WHEN 5  THEN 'Negotiated Fare'
            WHEN 6  THEN 'Group Ride'
            WHEN 99 THEN 'Unknown'
        END AS ratecode_label,

        CASE
            WHEN RatecodeID = 2 THEN 'Airport JFK'
            WHEN RatecodeID = 3 THEN 'Airport Newark'
            WHEN RatecodeID = 4 THEN 'Nassau/Westchester'
            WHEN RatecodeID = 5 THEN 'Negotiated'
            WHEN RatecodeID = 6 THEN 'Group Ride'
            ELSE 'Standard'
        END AS trip_type,

        (RatecodeID IN (2, 3) OR airport_fee > 0) AS is_airport_trip,

        store_and_fwd_flag,
        (store_and_fwd_flag = 'Y') AS is_store_and_fwd,

        PULocationID,
        DOLocationID,

        -- --------------------------------------------------------
        -- Paiement
        -- --------------------------------------------------------
        payment_type,

        CASE payment_type
            WHEN 0 THEN 'Flex Fare'
            WHEN 1 THEN 'Credit Card'
            WHEN 2 THEN 'Cash'
            WHEN 3 THEN 'No Charge'
            WHEN 4 THEN 'Dispute'
            WHEN 5 THEN 'Unknown'
            WHEN 6 THEN 'Voided Trip'
        END AS payment_type_label,

        fare_amount,
        tip_amount,

        CASE
            WHEN fare_amount > 0
            THEN ROUND(tip_amount / fare_amount * 100, 2)
            ELSE 0
        END AS tip_rate,

        (tip_amount > 0) AS has_tip,

        total_amount,
        extra,
        mta_tax,
        tolls_amount,
        improvement_surcharge,
        congestion_surcharge,
        airport_fee,

        -- Disponible uniquement à partir du 5 janvier 2025
        COALESCE(cbd_congestion_fee, 0) AS cbd_congestion_fee,

        ROUND(
            extra + mta_tax + improvement_surcharge
            + congestion_surcharge + COALESCE(cbd_congestion_fee, 0),
            2
        ) AS total_surcharges,

        CASE
            WHEN total_amount > 0
            THEN ROUND(fare_amount / total_amount * 100, 2)
            ELSE NULL
        END AS base_fare_ratio,

        -- --------------------------------------------------------
        -- Métadonnées ingestion
        -- --------------------------------------------------------
        _source_file,
        _loaded_at

    FROM source

    WHERE

        -- --------------------------------------------------------
        -- Période d'étude
        -- --------------------------------------------------------
        YEAR(tpep_pickup_datetime) BETWEEN 2024 AND 2025

        -- --------------------------------------------------------
        -- Cohérence temporelle
        -- --------------------------------------------------------
        AND tpep_dropoff_datetime > tpep_pickup_datetime

        AND DATEDIFF('minute', tpep_pickup_datetime, tpep_dropoff_datetime)
            BETWEEN 1 AND 300

        -- --------------------------------------------------------
        -- Cohérence financière
        -- --------------------------------------------------------
        AND fare_amount   BETWEEN 0 AND 500
        AND total_amount  BETWEEN 0 AND 500
        AND tip_amount    >= 0
        AND tolls_amount  >= 0

        -- --------------------------------------------------------
        -- Cohérence distance
        -- --------------------------------------------------------
        AND trip_distance BETWEEN 0.01 AND 200

        -- --------------------------------------------------------
        -- Passagers
        -- --------------------------------------------------------
        AND passenger_count > 0

        -- --------------------------------------------------------
        -- Codes TLC officiels (Data Dictionary 2025)
        -- --------------------------------------------------------
        AND RatecodeID IN (1, 2, 3, 4, 5, 6, 99)
        AND VendorID   IN (1, 2, 6, 7)

        -- --------------------------------------------------------
        -- Colonnes critiques
        -- --------------------------------------------------------
        AND PULocationID IS NOT NULL
        AND DOLocationID IS NOT NULL
)

SELECT * FROM cleaned
