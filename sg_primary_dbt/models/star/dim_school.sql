WITH schools AS (
    SELECT * FROM {{ ref('stg_primary_schools') }}
),

lifecycle AS (
    SELECT * FROM {{ ref('school_lifecycle') }}
),

joined AS (
    SELECT
        -- {{ dbt_utils.generate_surrogate_key(['school_name_clean']) }} AS school_key,
        COALESCE(s.school_name_clean, l.school_name_clean) as school_name_clean,
        s.address,
        s.postal_code,
        s.dgp_code,
        s.zone_code,
        s.type_code,
        s.nature_code,
        s.session_code,
        s.mainlevel_code,
        s.sap_ind,
        s.autonomous_ind,
        s.gifted_ind,
        s.ip_ind,
        s.mothertongue1_code,
        s.mothertongue2_code,
        s.mothertongue3_code,

        -- Lifecycle attributes from seed
        -- COALESCE to 'active' for schools not in lifecycle seed
        COALESCE(l.school_status, 'active')     AS school_status,
        l.inactive_from_year,
        l.inactive_to_year,
        l.merged_into,

        -- is_active is computed dynamically against current year
        -- so it self-updates without seed file changes when
        -- a relocated school resumes intake
        CASE
            WHEN COALESCE(l.school_status, 'active') = 'active'
                THEN TRUE
            WHEN l.school_status = 'merged'
                THEN FALSE
            WHEN l.school_status = 'relocated_gap'
                 AND EXTRACT(YEAR FROM CURRENT_DATE()) > l.inactive_to_year
                THEN TRUE
            WHEN l.school_status = 'relocated_gap'
                 AND EXTRACT(YEAR FROM CURRENT_DATE()) <= l.inactive_to_year
                THEN FALSE
            ELSE FALSE
        END                                     AS is_active

    FROM schools s
    FULL OUTER JOIN lifecycle l
    ON s.school_name_clean = l.school_name_clean
),

final as (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['school_name_clean']) }} AS school_key,
        *
    FROM joined        
)

SELECT * FROM final