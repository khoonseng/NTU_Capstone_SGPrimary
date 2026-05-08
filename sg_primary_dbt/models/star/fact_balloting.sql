{{
  config(
    materialized='table',
    partition_by={
      "field": "registration_year",
      "data_type": "int64",
      "range": {"start": 2009, "end": 2051, "interval": 1}
    },
    cluster_by=["school_name_clean", "phase_normalised"]
  )
}}

-- One row per school × year × phase.
WITH balloting AS (
    SELECT * FROM {{ ref('stg_sgschooling_balloting') }}
),

schools AS (
    SELECT 
        school_key, 
        school_name_clean
    FROM {{ ref('dim_school') }}
),

joined AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key([
            'b.school_name_clean',
            'b.registration_year',
            'b.phase_normalised'
        ]) }}                                   AS balloting_key,

        s.school_key,
        b.school_name_clean,
        b.phase_normalised,
        b.phase_raw,
        b.registration_year,
        b.total_vacancy,
        b.vacancy,
        b.applied,
        b.taken,
        b.has_full_figures,
        b.subscription_rate,
        b.remaining_places,
        b.is_over_enrolled,
        b.over_enrolled_count,
        b.ballot_scenario_code,
        b.ballot_description,
        b.ballot_applicants,
        b.ballot_vacancies,
        b.ballot_chance_pct,
        b.scraped_at

    FROM balloting b
    LEFT JOIN schools s
    ON b.school_name_clean = s.school_name_clean
)

SELECT * FROM joined