{{ config(materialized='table') }}

WITH all_dates AS (
    SELECT CAST(order_purchase_timestamp AS DATE) AS date_day FROM {{ ref('stg_orders') }}
    UNION ALL SELECT CAST(order_approved_at AS DATE) FROM {{ ref('stg_orders') }}
    UNION ALL SELECT CAST(order_delivered_carrier_date AS DATE) FROM {{ ref('stg_orders') }}
    UNION ALL SELECT CAST(order_delivered_customer_date AS DATE) FROM {{ ref('stg_orders') }}
    UNION ALL SELECT CAST(order_estimated_delivery_date AS DATE) FROM {{ ref('stg_orders') }}
    UNION ALL SELECT CAST(review_creation_date AS DATE) FROM {{ ref('stg_order_reviews') }}
    UNION ALL SELECT CAST(review_answer_timestamp AS DATE) FROM {{ ref('stg_order_reviews') }}
    UNION ALL SELECT CAST(shipping_limit_date AS DATE) FROM {{ ref('stg_order_items') }}
), bounds AS (
    SELECT MIN(date_day) AS min_date, MAX(date_day) AS max_date
    FROM all_dates
    WHERE date_day IS NOT NULL
), calendar AS (
    SELECT UNNEST(GENERATE_SERIES(min_date, max_date, INTERVAL 1 DAY))::DATE AS date_day
    FROM bounds
)

SELECT
    CAST(STRFTIME(date_day, '%Y%m%d') AS INTEGER) AS date_key,
    date_day,
    YEAR(date_day) AS year,
    QUARTER(date_day) AS quarter,
    MONTH(date_day) AS month,
    MONTHNAME(date_day) AS month_name,
    WEEK(date_day) AS week_of_year,
    DAY(date_day) AS day_of_month,
    DAYOFWEEK(date_day) AS day_of_week,
    DAYNAME(date_day) AS day_name,
    DAYOFWEEK(date_day) IN (0, 6) AS is_weekend
FROM calendar
