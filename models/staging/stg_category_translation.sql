{{ config(materialized='view') }}

SELECT
    product_category_name,
    product_category_name_english
FROM {{ source('olist_raw', 'category_translation') }}
