-- Mart table: latest vacancy snapshot per school × phase × year.
--
-- The producer emits up to 6 slots per school per phase (3 days × 2 snapshots).
-- This mart keeps only the most recent slot received, ordered by snapshot_timestamp
-- DESC — so the latest midday or end-of-day snapshot is always surfaced.
--
-- Joined with dim_school to carry zone_code and dgp_code. This allows the API
-- to filter by zone/estate directly (same pattern as the main recommend query)
-- without needing to pass a list of school names as a query parameter.
--
-- The API reads this table for Mode 2 interim data. An empty result means
-- no snapshot has been produced yet for that phase/year combination.

WITH latest AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY school_name, phase, registration_year
            ORDER BY snapshot_timestamp DESC
        ) AS _row_num
    FROM {{ ref('stg_p1_vacancy_snapshots') }}
)

SELECT
    s.school_name,
    s.phase,
    s.registration_year,
    s.simulation_day,
    s.snapshot_type,
    s.snapshot_timestamp,
    s.vacancy_at_open,
    s.vacancy_remaining,
    s.applied_count,
    s.pct_filled,
    d.zone_code,
    d.dgp_code
FROM latest s
LEFT JOIN {{ ref('dim_school') }} d
    ON s.school_name = d.school_name_clean
WHERE s._row_num = 1
