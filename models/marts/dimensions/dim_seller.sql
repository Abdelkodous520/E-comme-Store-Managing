{{ config(materialized='table') }}

SELECT
    ROW_NUMBER() OVER (ORDER BY seller_id)::BIGINT AS seller_key,
    seller_id,
    CAST(seller_zip_code_prefix AS VARCHAR) AS postal_code,
    seller_city AS city,
    seller_state AS state,
    'Brazil' AS country
FROM {{ ref('stg_sellers') }}
