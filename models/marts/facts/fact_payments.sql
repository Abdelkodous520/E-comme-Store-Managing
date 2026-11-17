
{{ config(materialized='table') }}

SELECT
    p.order_id,
    p.payment_sequential,
    o.customer_id,
    dc.customer_key,
    CAST(STRFTIME(CAST(o.order_purchase_timestamp AS TIMESTAMP), '%Y%m%d') AS INTEGER)
        AS date_achat_key,
    p.payment_type,
    p.payment_installments,
    CAST(p.payment_value AS DOUBLE) AS payment_value

FROM {{ ref('stg_order_payments') }} AS p
LEFT JOIN {{ ref('stg_orders') }} AS o
    ON p.order_id = o.order_id
LEFT JOIN {{ ref('dim_customer') }} AS dc
    ON o.customer_id = dc.customer_id

WHERE p.order_id IS NOT NULL
