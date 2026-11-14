
{{ config(materialized='view') }}

SELECT
    COUNT(DISTINCT order_id) AS nb_commandes

FROM {{ ref('fact_order_lines') }}

WHERE order_status NOT IN ('canceled', 'unavailable')
