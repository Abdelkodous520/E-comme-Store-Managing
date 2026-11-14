
{{ config(materialized='table') }}

SELECT
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    CAST(payment_value AS DOUBLE) AS payment_value

FROM {{ ref('stg_order_payments') }}

WHERE order_id IS NOT NULL