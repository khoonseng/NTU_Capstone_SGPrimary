-- =============================================================================
-- mart_school_analysis.sql
--
-- Grain: one row per school × phase × year, scoped to phases 2B, 2C, 2C(S), 3
--
-- Purpose:
--   1. Pre-aggregated feature store for ML prediction model (Week 3-4)
--   2. API response source for per-school ballot history and predictions
--   3. Recommendation engine input — ranks schools by ballot difficulty
--
-- Includes all years 2009-2025 and all schools (active, relocated, merged)
-- because:
--   - Pre-2019 missing figures only affect phases 1/2A — not in scope here
--   - Inactive schools have historical data useful for trend features
--   - API needs to surface merger/relocation context to parents
--
-- Note: window function trend features (3yr avg, 5yr avg etc.) require
-- sufficient prior year rows to be meaningful. Rows with fewer than 3
-- prior years will have partially populated trend columns — this is
-- intentional and expected for early years (2009, 2010, 2011).
-- =============================================================================

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

WITH

-- ---------------------------------------------------------------------------
-- STEP 1: Filter fact_balloting to relevant phases only
-- Phases 2B, 2C, 2C(S), 3 are the competitive open-access phases that
-- parents without school ties compete in. Phases 1 and 2A are excluded
-- because they are priority phases with guaranteed or semi-guaranteed entry
-- and are not the basis for ballot difficulty predictions.
-- Phases 2A(1), 2A(2), 2 will be considered in future
-- ---------------------------------------------------------------------------
balloting_filtered AS (
    SELECT *
    FROM {{ ref('fact_balloting') }}
    WHERE phase_normalised IN ('2B', '2C', '2C(S)', '3')
),

-- ---------------------------------------------------------------------------
-- STEP 2: Join school attributes from dim_school
-- Brings in stable descriptive attributes used as ML features and
-- API response enrichment. school_status and lifecycle columns are
-- needed to compute is_active_for_year in the next CTE.
-- ---------------------------------------------------------------------------
with_school AS (
    SELECT
        -- ── Fact columns ────────────────────────────────────────────────────
        b.school_key,
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

        -- ── School stable attributes (ML features) ──────────────────────────
        s.postal_code,
        s.dgp_code,
        s.zone_code,
        s.type_code,
        s.nature_code,
        s.session_code,
        s.sap_ind,
        s.autonomous_ind,
        s.gifted_ind,
        s.ip_ind,
        s.mothertongue1_code,
        s.mothertongue2_code,
        s.mothertongue3_code,

        -- ── Current activity status (for API display) ────────────────────────
        s.school_status,
        s.is_active,                    -- current status as of today
        s.inactive_from_year,
        s.inactive_to_year,
        s.merged_into,
        s.school_status_description

    FROM balloting_filtered b
    LEFT JOIN {{ ref('dim_school') }} s
        ON b.school_key = s.school_key
),

-- ---------------------------------------------------------------------------
-- STEP 3: Compute is_active_for_year
--
-- Answers: "Was this school accepting P1 registrations in this specific year?"
-- This is independent of today's is_active flag, which answers:
-- "Is this school currently accepting registrations?"
--
-- Three scenarios:
--   Active school (no lifecycle record): always TRUE
--   Merged school: TRUE before inactive_from_year, FALSE from that year on
--   Relocated school: TRUE before gap, FALSE during gap, TRUE after gap
--
-- Example — Pioneer Primary (inactive_from=2021, inactive_to=2024):
--   2020 row → TRUE  (before gap)
--   2022 row → FALSE (during gap — but this row won't exist in fact_balloting)
--   2025 row → TRUE  (after gap, school resumed)
-- ---------------------------------------------------------------------------
-- with_activity AS (
--     SELECT
--         *,
--         CASE
--             WHEN school_status = 'active'
--                 THEN TRUE
--             WHEN school_status = 'merged'
--                 THEN registration_year < inactive_from_year
--             WHEN school_status = 'relocated_gap'
--                 THEN registration_year < inactive_from_year
--                   OR registration_year > COALESCE(inactive_to_year, 9999)
--             ELSE TRUE
--         END                                         AS is_active_for_year

--     FROM with_school
-- ),

-- ---------------------------------------------------------------------------
-- STEP 4: Citizenship and distance band encoding
--
-- Derives structured eligibility signals from ballot_scenario_code.
-- These are used by the API to filter recommendations by citizenship
-- and distance band when a parent inputs their profile.
--
-- ballot_citizen_group: who was required to ballot (SC or PR)
-- ballot_distance_band: at what distance ballot was triggered
--
-- Both NULL when no balloting occurred — meaning all eligible applicants
-- in that phase were admitted without balloting.
-- ---------------------------------------------------------------------------
with_ballot_encoding AS (
    SELECT
        *,
        CASE
            WHEN ballot_scenario_code LIKE 'SC%' THEN 'SC'
            WHEN ballot_scenario_code LIKE 'PR%' THEN 'PR'
            -- how to handle foreigners?
            ELSE NULL
        END                                         AS ballot_citizen_group,

        CASE
            WHEN ballot_scenario_code IN ('SC<1', 'PR<1') THEN 'within_1km'
            WHEN ballot_scenario_code IN ('SC<1#', 'PR<1#') THEN 'within_1km_no_leftover'
            WHEN ballot_scenario_code IN ('SC1-2', 'PR1-2') THEN '1_to_2km'
            WHEN ballot_scenario_code IN ('SC<2#', 'PR<2#') THEN 'within_2km_no_leftover'
            WHEN ballot_scenario_code IN ('SC>2', 'PR>2') THEN 'beyond_2km'
            WHEN ballot_scenario_code IN ('SC#') THEN 'beyond_2km_no_leftover'
            ELSE NULL
        END                                         AS ballot_distance_band

    FROM with_school
),

-- ---------------------------------------------------------------------------
-- STEP 5: Historical trend features via window functions
--
-- All windows partition by school_key + phase_normalised and order by
-- registration_year, so trends are computed independently per school
-- per phase. A school's Phase 2C trend is never contaminated by its
-- Phase 2B data.
--
-- ROWS BETWEEN N PRECEDING AND CURRENT ROW means the window includes
-- the current year — so "3yr avg" for 2025 covers 2023, 2024, 2025.
-- For early years (e.g. 2009), fewer than 3 prior rows exist so the
-- window shrinks automatically — BigQuery handles this correctly.
--
-- subscription_rate_yoy_change: positive = increasing demand (worse for parents)
--                               negative = decreasing demand (better for parents)
-- ballot_occurrences_last_3yr:  0 = no recent balloting (low risk)
--                               3 = balloted every year for 3 years (high risk)
-- vacancy_yoy_change:           negative = school shrinking intake (higher pressure)
--                               positive = school growing intake (lower pressure)
-- ---------------------------------------------------------------------------
with_trends AS (
    SELECT
        *,

        -- 3-year rolling average subscription rate
        -- Primary trend signal for ML model — recent demand is most predictive
        AVG(subscription_rate) OVER (
            PARTITION BY school_key, phase_normalised
            ORDER BY registration_year
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        )                                           AS subscription_rate_3yr_avg,

        -- 5-year rolling average subscription rate
        -- Longer baseline — smooths out single-year anomalies (e.g. COVID 2021)
        AVG(subscription_rate) OVER (
            PARTITION BY school_key, phase_normalised
            ORDER BY registration_year
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        )                                           AS subscription_rate_5yr_avg,

        -- Year-over-year change in subscription rate
        -- Captures momentum: is demand rising or falling?
        subscription_rate - LAG(subscription_rate) OVER (
            PARTITION BY school_key, phase_normalised
            ORDER BY registration_year
        )                                           AS subscription_rate_yoy_change,

        -- Count of years where balloting occurred in last 3 years
        -- Encodes ballot streak: 3/3 = consistently oversubscribed = high risk
        SUM(
            CASE WHEN ballot_scenario_code IS NOT NULL THEN 1 ELSE 0 END
        ) OVER (
            PARTITION BY school_key, phase_normalised
            ORDER BY registration_year
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        )                                           AS ballot_occurrences_last_3yr,

        -- 5-year ballot occurrence count
        SUM(
            CASE WHEN ballot_scenario_code IS NOT NULL THEN 1 ELSE 0 END
        ) OVER (
            PARTITION BY school_key, phase_normalised
            ORDER BY registration_year
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        )                                           AS ballot_occurrences_last_5yr,

        -- Year-over-year vacancy change
        -- Negative = school shrinking capacity = more competition for fewer places
        vacancy - LAG(vacancy) OVER (
            PARTITION BY school_key, phase_normalised
            ORDER BY registration_year
        )                                           AS vacancy_yoy_change,

        -- 3-year average vacancy
        -- Smoothed supply signal — more stable than single-year vacancy
        AVG(vacancy) OVER (
            PARTITION BY school_key, phase_normalised
            ORDER BY registration_year
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        )                                           AS vacancy_3yr_avg

    FROM with_ballot_encoding
),

with_ballot_risk AS (
    SELECT 
        *,
        
        -- Risk level encoding for API display
        -- Derived from ballot_occurrences_last_3yr + subscription_rate_3yr_avg
        -- Computed here as a convenience label — ML model uses raw features
        CASE
            WHEN ballot_occurrences_last_3yr = 3
            AND subscription_rate_3yr_avg > 1.2                                 
            THEN 'HIGH'

            WHEN ballot_occurrences_last_3yr >= 1   
            AND subscription_rate_3yr_avg > 1.2                               
            THEN 'MEDIUM'
            
            ELSE 'LOW'
        END                                         AS ballot_risk_level
        
    FROM with_trends
),

-- ---------------------------------------------------------------------------
-- STEP 6: Final column selection and ordering
-- Surrogate key for the mart row — unique per school × phase × year
-- ---------------------------------------------------------------------------
final AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key([
            'school_key',
            'phase_normalised',
            'registration_year'
        ]) }}                                       AS analysis_key,

        -- ── Identity ────────────────────────────────────────────────────────
        school_key,
        school_name_clean,
        phase_normalised,
        phase_raw,
        registration_year,

        -- ── School attributes (ML features + API enrichment) ─────────────────
        postal_code,
        dgp_code,
        zone_code,
        type_code,
        nature_code,
        session_code,
        sap_ind,
        autonomous_ind,
        gifted_ind,
        ip_ind,
        mothertongue1_code,
        mothertongue2_code,
        mothertongue3_code,

        -- ── Activity status ──────────────────────────────────────────────────
        school_status,
        is_active,
        -- is_active_for_year,
        inactive_from_year,
        inactive_to_year,
        merged_into,
        school_status_description,

        -- ── Registration figures ─────────────────────────────────────────────
        total_vacancy,
        vacancy,
        applied,
        taken,
        has_full_figures,
        subscription_rate,
        remaining_places,
        is_over_enrolled,
        over_enrolled_count,

        -- ── Ballot details ───────────────────────────────────────────────────
        ballot_scenario_code,
        ballot_description,
        ballot_applicants,
        ballot_vacancies,
        ballot_chance_pct,
        ballot_citizen_group,
        ballot_distance_band,

        -- ── Historical trend features (ML model inputs) ──────────────────────
        ROUND(subscription_rate_3yr_avg, 4) as subscription_rate_3yr_avg,
        ROUND(subscription_rate_5yr_avg, 4) as subscription_rate_5yr_avg,
        ROUND(subscription_rate_yoy_change, 4) as subscription_rate_yoy_change,
        ballot_occurrences_last_3yr,
        ballot_occurrences_last_5yr,
        vacancy_yoy_change,
        ROUND(vacancy_3yr_avg, 2) as vacancy_3yr_avg,
        ballot_risk_level

    FROM with_ballot_risk
)

SELECT * FROM final
