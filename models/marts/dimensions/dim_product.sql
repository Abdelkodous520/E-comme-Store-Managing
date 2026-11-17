{{ config(materialized='table') }}

SELECT
    ROW_NUMBER() OVER (ORDER BY p.product_id)::BIGINT AS product_key,
    p.product_id,
    p.product_category_name AS category_name_pt,
    COALESCE(t.product_category_name_english, 'unknown') AS category_name_en,
    p.product_name_lenght AS name_length,
    p.product_description_lenght AS description_length,
    p.product_photos_qty AS photos_qty,
    p.product_weight_g AS weight_g,
    p.product_length_cm AS length_cm,
    p.product_height_cm AS height_cm,
    p.product_width_cm AS width_cm
FROM {{ ref('stg_products') }} AS p
LEFT JOIN {{ ref('stg_category_translation') }} AS t
    ON p.product_category_name = t.product_category_name
