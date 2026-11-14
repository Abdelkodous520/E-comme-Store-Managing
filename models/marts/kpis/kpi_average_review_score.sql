
{{ config(materialized='view') }}

SELECT
    ROUND(AVG(review_score), 2)
        AS note_moyenne,

    COUNT(*) AS nb_lignes_avis

FROM {{ ref('fact_reviews') }}

WHERE review_score BETWEEN 1 AND 5
