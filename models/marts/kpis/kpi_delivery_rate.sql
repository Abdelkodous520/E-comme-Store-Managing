
{{ config(materialized='view') }}

SELECT
    COUNT(DISTINCT order_id) AS nb_commandes_valides,

    COUNT(DISTINCT order_id) FILTER (
        WHERE order_status = 'delivered'
    ) AS nb_commandes_livrees,

    ROUND(
        100.0 * COUNT(DISTINCT order_id) FILTER (
            WHERE order_status = 'delivered'
        )
        / NULLIF(COUNT(DISTINCT order_id), 0),
        2
    ) AS taux_livrees_pct

FROM {{ ref('fact_order_items') }}

WHERE order_status NOT IN ('canceled', 'unavailable')
