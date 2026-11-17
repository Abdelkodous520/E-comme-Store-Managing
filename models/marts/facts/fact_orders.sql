{{ config(materialized='table') }}

SELECT
    o.order_id,
    o.customer_id,
    dc.customer_key,
    CAST(strftime(CAST(o.order_purchase_timestamp AS TIMESTAMP), '%Y%m%d') AS INTEGER)
        AS date_achat_key,
    CAST(strftime(CAST(o.order_delivered_customer_date AS TIMESTAMP), '%Y%m%d') AS INTEGER)
        AS date_livraison_key,
    CAST(strftime(CAST(o.order_estimated_delivery_date AS TIMESTAMP), '%Y%m%d') AS INTEGER)
        AS date_estimee_key,
    o.order_status,
    1 AS order_count,
    CASE
        WHEN o.order_status = 'delivered'
         AND o.order_purchase_timestamp IS NOT NULL
         AND o.order_delivered_customer_date IS NOT NULL
        THEN date_diff(
            'second',
            CAST(o.order_purchase_timestamp AS TIMESTAMP),
            CAST(o.order_delivered_customer_date AS TIMESTAMP)
        ) / 86400.0
    END AS duree_livraison_jours,
    CASE
        WHEN o.order_status = 'delivered'
         AND o.order_delivered_customer_date IS NOT NULL
         AND o.order_estimated_delivery_date IS NOT NULL
        THEN CASE
            WHEN CAST(o.order_delivered_customer_date AS TIMESTAMP)
               > CAST(o.order_estimated_delivery_date AS TIMESTAMP) THEN 1
            ELSE 0
        END
    END AS retard_flag
FROM {{ ref('stg_orders') }} AS o
LEFT JOIN {{ ref('dim_customer') }} AS dc
    ON o.customer_id = dc.customer_id
