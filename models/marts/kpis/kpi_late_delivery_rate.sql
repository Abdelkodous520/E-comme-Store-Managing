

{{ config(materialized='view') }}

SELECT
    COUNT(retard_flag)
        AS nb_livrees_evaluables,

    SUM(retard_flag)
        AS nb_livrees_en_retard,

    ROUND(
        100.0 * SUM(retard_flag)
        / NULLIF(COUNT(retard_flag), 0),
        2
    ) AS taux_retard_pct

FROM {{ ref('fact_orders') }}

WHERE order_status = 'delivered'
  AND retard_flag IS NOT NULL
