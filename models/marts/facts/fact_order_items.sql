
{{ config(materialized='table') }}

WITH lignes AS (

    SELECT
        o.order_id,
        COALESCE(oi.order_item_id, 0) AS order_item_id,

        o.customer_id,
        COALESCE(oi.product_id, '-1') AS product_id,
        COALESCE(oi.seller_id, '-1') AS seller_id,
        dc.customer_key,
        dp.product_key,
        ds.seller_key,

        o.order_status,

        CAST(o.order_purchase_timestamp AS TIMESTAMP) AS t_achat,
        CAST(o.order_delivered_customer_date AS TIMESTAMP) AS t_livre,
        CAST(o.order_estimated_delivery_date AS TIMESTAMP) AS t_estime,

        oi.price,
        oi.freight_value,

        CASE
            WHEN oi.order_id IS NULL THEN 0
            ELSE 1
        END AS item_count,

        ROW_NUMBER() OVER (
            PARTITION BY o.order_id
            ORDER BY COALESCE(oi.order_item_id, 0)
        ) AS rang

    FROM {{ ref('stg_orders') }} AS o

    LEFT JOIN {{ ref('stg_order_items') }} AS oi
        ON o.order_id = oi.order_id
    LEFT JOIN {{ ref('dim_customer') }} AS dc
        ON o.customer_id = dc.customer_id
    LEFT JOIN {{ ref('dim_product') }} AS dp
        ON oi.product_id = dp.product_id
    LEFT JOIN {{ ref('dim_seller') }} AS ds
        ON oi.seller_id = ds.seller_id
),

lignes_preparees AS (

    SELECT
        *,

        CASE
            WHEN rang = 1 THEN 1
            ELSE 0
        END AS order_count,

        CASE
            WHEN rang = 1
                 AND order_status = 'delivered'
                 AND t_achat IS NOT NULL
                 AND t_livre IS NOT NULL
            THEN date_diff('second', t_achat, t_livre) / 86400.0
        END AS duree_livraison_jours,

        CASE
            WHEN rang = 1
                 AND order_status = 'delivered'
                 AND t_livre IS NOT NULL
                 AND t_estime IS NOT NULL
            THEN
                CASE
                    WHEN t_livre > t_estime THEN 1
                    ELSE 0
                END
        END AS retard_flag

    FROM lignes
)

SELECT
    order_id,
    order_item_id,

    customer_id,
    product_id,
    seller_id,
    customer_key,
    product_key,
    seller_key,

    CAST(strftime(t_achat, '%Y%m%d') AS INTEGER)
        AS date_achat_key,

    CAST(strftime(t_livre, '%Y%m%d') AS INTEGER)
        AS date_livraison_key,

    CAST(strftime(t_estime, '%Y%m%d') AS INTEGER)
        AS date_estimee_key,

    order_status,

    price,
    freight_value,

    item_count,
    order_count,

    duree_livraison_jours,
    retard_flag

FROM lignes_preparees
