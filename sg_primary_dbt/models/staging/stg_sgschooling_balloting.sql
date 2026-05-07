-- =============================================================================
-- stg_sgschooling_balloting.sql
-- Staging model for raw sgschooling balloting data.
--
-- Responsibilities:
--   1. Fix curly apostrophe in school names
--   2. Map raw school names to canonical names via school_name_mapping seed
--   3. Normalise raw phase labels to phase_normalised via phases seed
--   4. Derive analytical flags and metrics (has_full_figures, subscription_rate, etc.)
--   5. Preserve all raw columns for auditability
-- =============================================================================

WITH

-- ---------------------------------------------------------------------------
-- STEP 1: Base — read from raw source, fix curly apostrophe immediately
--
-- The curly right single quotation mark (Unicode U+2019) appears in school
-- names scraped from sgschooling.com e.g. "CHIJ ST. NICHOLAS GIRLS'".
-- data.gov.sg uses the straight ASCII apostrophe (U+0027) instead.
-- REPLACE() swaps U+2019 → U+0027 before any joining occurs, ensuring the
-- name is in canonical form for the seed lookup in the next CTE.
--
-- UPPER(TRIM(...)) removes leading/trailing whitespace and standardises case,
-- matching the format used in school_name_mapping.sgschooling_name.
-- ---------------------------------------------------------------------------
base AS (
    SELECT
        -- Fix curly apostrophe and standardise casing for joining
        UPPER(TRIM(
            REPLACE(school_name, '\u2019', "'")
        ))                                          AS school_name_raw_clean,

        -- Normalise "Phase 1" → "1" to be consistent with other phase labels
        -- e.g. "2A", "2B", "2C(S)". All other phases do not carry the word "Phase".
        CASE
            WHEN TRIM(phase) = 'Phase 1' THEN '1'
            ELSE TRIM(phase)
        END                                         AS phase_raw_normalised,

        -- Preserve original values for audit trail
        school_name                                 AS school_name_original,
        phase                                       AS phase_original,

        -- Registration figures
        total_vacancy,
        vacancy,
        applied,
        taken,

        -- Ballot details
        ballot_scenario_code,
        ballot_description,
        ballot_applicants,
        ballot_vacancies,
        ballot_chance_pct,

        -- Pipeline metadata
        registration_year,
        scraped_at

    FROM {{ source('sg_moe', 'raw_sgschooling_balloting') }}
),

-- ---------------------------------------------------------------------------
-- STEP 2: Apply school name mapping seed
--
-- school_name_mapping.csv maps sgschooling raw names → canonical names
-- sourced from data.gov.sg raw_schools table. This covers two classes
-- of mismatch:
--   a) Character differences: curly apostrophe vs straight apostrophe
--      (already fixed by REPLACE above, but mapping handles edge cases)
--   b) Name truncations: sgschooling omits "SCHOOL" suffix for some schools
--      e.g. "CHIJ ST. NICHOLAS GIRLS'" → "CHIJ ST. NICHOLAS GIRLS' SCHOOL"
--
-- COALESCE logic:
--   If a mapping exists → use canonical_name (data.gov.sg version)
--   If no mapping exists → school name was already consistent, use as-is
--
-- This CTE is the ONLY place school_name_mapping is ever referenced.
-- All downstream models consume school_name_clean without needing to
-- know the mapping seed exists.
-- ---------------------------------------------------------------------------
name_mapped AS (
    SELECT
        b.*,
        COALESCE(
            m.moe_school_name,
            b.school_name_raw_clean
        )                                           AS school_name_clean
    FROM base b
    LEFT JOIN {{ ref('school_name_mapping') }} m
        ON b.school_name_raw_clean = REPLACE(m.sgschooling_name, '\u2019', "'")
),

-- ---------------------------------------------------------------------------
-- STEP 3: Apply phase normalisation via phases seed
--
-- The phases seed is the single source of truth for valid phase codes.
-- Joining here serves two purposes:
--   a) Derive phase_normalised — the standardised phase label used across
--      all downstream models. Pre-2022 "2A(1)" maps to "2A", while "2A(2)"
--      remains distinct since it represented a different eligibility group.
--   b) Validate that every scraped phase exists in the seed. Any phase not
--      found in the seed will produce phase_normalised = NULL, which your
--      dbt not_null test will catch immediately.
--
-- The join key is phase_raw (the raw scraped phase after "Phase 1" → "1"
-- correction), matched against phases.phase_raw in the seed file.
-- ---------------------------------------------------------------------------
phase_mapped AS (
    SELECT
        n.*,
        p.phase_normalised,
        p.is_competitive
    FROM name_mapped n
    LEFT JOIN {{ ref('phases') }} p
        ON n.phase_raw_normalised = p.phase_raw
),

-- ---------------------------------------------------------------------------
-- STEP 4: Compute school-level totals using window function
--
-- SUM(taken) OVER (PARTITION BY school_name_clean, registration_year)
-- aggregates taken across all phases for a given school and year.
-- This is a window function — it does not collapse rows like GROUP BY would.
-- Every phase row retains its own data but gains access to the school-level
-- total, which is what is_over_enrolled needs for its comparison.
--
-- total_vacancy comes from the raw column (declared school capacity),
-- not SUM of per-phase vacancy figures. We take MAX() here because
-- total_vacancy is repeated identically across all phase rows for a
-- school-year — MAX() is just a safe way to carry it through without
-- collapsing rows.
-- ---------------------------------------------------------------------------
school_totals AS (
    SELECT
        *,
        SUM(taken) OVER (
            PARTITION BY school_name_clean, registration_year
        )                                           AS total_taken_all_phases
    FROM phase_mapped
),

-- ---------------------------------------------------------------------------
-- STEP 5: Derive analytical columns
--
-- has_full_figures:
--   MOE only published vacancy and applied counts for phases 1, 2A(1), 2A(2)
--   from 2019 onwards. For earlier years these fields are genuinely NULL —
--   not a scraping failure. This flag distinguishes intentional NULLs from
--   unexpected ones, allowing dbt tests to apply not_null conditionally.
--
-- subscription_rate:
--   applied / vacancy. Represents demand pressure per phase.
--   Values above 1.0 are valid and expected for oversubscribed phases
--   e.g. applied=134, vacancy=109 → subscription_rate=1.23 (123% subscribed).
--   NULL when has_full_figures=FALSE (no vacancy data) or vacancy=0
--   (avoids division by zero; vacancy=0 means all places were filled
--   in earlier phases so this phase was never opened).
--
-- remaining_places:
--   vacancy - taken. Negative values are valid — they indicate over-enrolment
--   where MOE admitted more students than the published vacancy figure.
--   This happens legitimately in Phase 1 (siblings guaranteed entry) and
--   when MOE adjusts intakes mid-exercise.
--
-- is_over_enrolled:
--   TRUE when total taken > total vacancy.
-- ---------------------------------------------------------------------------
final AS (
    SELECT
        -- ── Identity ────────────────────────────────────────────────────────
        school_name_clean,
        school_name_original,

        -- ── Phase ───────────────────────────────────────────────────────────
        phase_normalised,
        phase_raw_normalised                        AS phase_raw,
        -- phase_original,
        -- is_competitive,

        -- ── Registration figures ─────────────────────────────────────────────
        total_vacancy,
        vacancy,
        applied,
        taken,

        -- ── Derived flags and metrics ────────────────────────────────────────
        CASE
            WHEN phase_normalised IN ('1', '2A(1)', '2A(2)', '2A') AND registration_year < 2019       
                THEN FALSE
            ELSE 
                TRUE
        END                                         AS has_full_figures,

        CASE
            WHEN phase_normalised IN ('1', '2A(1)', '2A(2)', '2A') AND registration_year < 2019       
                THEN NULL
            WHEN vacancy IS NULL OR vacancy = 0     
                THEN NULL
            ELSE 
                ROUND(SAFE_DIVIDE(applied, vacancy), 4)
        END                                         AS subscription_rate,

        CASE
            WHEN phase_normalised IN ('1', '2A(1)', '2A(2)', '2A') AND registration_year < 2019       
                THEN NULL
            WHEN vacancy IS NULL                    
                THEN NULL
            ELSE 
                vacancy - taken
        END                                         AS remaining_places,

        CASE
            WHEN total_vacancy IS NULL              THEN NULL
            ELSE total_taken_all_phases > total_vacancy
        END                                         AS is_over_enrolled,

        CASE
            WHEN total_vacancy IS NULL              THEN NULL
            ELSE total_taken_all_phases - total_vacancy
        END                                         AS over_enrolled_count,

        -- ── Ballot details ───────────────────────────────────────────────────
        ballot_scenario_code,
        ballot_description,
        ballot_applicants,
        ballot_vacancies,
        ballot_chance_pct,

        -- ── Pipeline metadata ────────────────────────────────────────────────
        registration_year,
        scraped_at

    FROM school_totals
)

SELECT * FROM final
