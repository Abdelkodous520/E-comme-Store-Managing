{{ config(materialized='table') }}

SELECT
    ROW_NUMBER() OVER (ORDER BY customer_id)::BIGINT AS customer_key,
    customer_id,
    customer_unique_id,
    CAST(customer_zip_code_prefix AS VARCHAR) AS postal_code,
    customer_city AS city,
    customer_state AS state,
    'Brazil' AS country
FROM {{ ref('stg_customers') }}
