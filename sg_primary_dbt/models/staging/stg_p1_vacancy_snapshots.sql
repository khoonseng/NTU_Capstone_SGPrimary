-- Staging model for raw Kafka vacancy snapshot events.
--
-- Deduplicates on natural key (school_name, phase, registration_year,
-- simulation_day, snapshot_type). Each replay of the producer creates
-- new event_id UUIDs but represents the same logical snapshot slot.
-- scraped_at DESC picks the most recently produced message per slot.
--
-- No school name reconciliation needed — the producer seeds from
-- mart_school_analysis so canonical names are already correct.

WITH deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY school_name, phase, registration_year, simulation_day, snapshot_type
            ORDER BY snapshot_timestamp DESC
        ) AS _row_num
    FROM {{ source('sg_moe', 'raw_p1_vacancy_snapshots') }}
)

SELECT
    event_id,
    school_name,
    phase,
    registration_year,
    simulation_day,
    snapshot_type,
    snapshot_timestamp,
    vacancy_at_open,
    vacancy_remaining,
    applied_count,
    pct_filled
FROM deduped
WHERE _row_num = 1
