
{{ config(materialized='view') }}

WITH commandes_clients AS (

    SELECT
        customer_id,
        COUNT(DISTINCT order_id) AS nb_commandes

    FROM {{ ref('fact_order_items') }}

    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND order_count = 1

    GROUP BY customer_id

),

personnes AS (

    SELECT
        c.customer_unique_id,
        SUM(cc.nb_commandes) AS nb_commandes

    FROM commandes_clients AS cc

    INNER JOIN {{ ref('stg_customers') }} AS c
        ON cc.customer_id = c.customer_id

    GROUP BY c.customer_unique_id

)

SELECT

    COUNT(*) FILTER (
        WHERE nb_commandes >= 2
    ) AS nb_clients_recurrents,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE nb_commandes >= 2
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS taux_clients_recurrents_pct

FROM personnes
