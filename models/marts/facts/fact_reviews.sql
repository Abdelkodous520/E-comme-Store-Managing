{{ config(materialized='table') }}

WITH avis AS (

    SELECT
        order_id,
        review_id,
        review_score,
        review_comment_title,
        review_comment_message,
        review_creation_date,
        review_answer_timestamp,

        ROW_NUMBER() OVER (
            ORDER BY
                order_id,
                review_creation_date,
                review_answer_timestamp,
                review_score,
                review_comment_title,
                review_comment_message
        ) AS review_row_key

    FROM {{ ref('stg_order_reviews') }}

)

SELECT
    review_row_key,
    order_id,
    review_id,

    CAST(review_score AS INTEGER) AS review_score,

    review_comment_title,
    review_comment_message,

    CAST(review_creation_date AS TIMESTAMP)
        AS review_creation_date,

    CAST(review_answer_timestamp AS TIMESTAMP)
        AS review_answer_timestamp,

    CAST(
        strftime(
            CAST(review_creation_date AS TIMESTAMP),
            '%Y%m%d'
        ) AS INTEGER
    ) AS review_date_key

FROM avis