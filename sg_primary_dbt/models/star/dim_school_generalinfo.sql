SELECT
    {{ dbt_utils.generate_surrogate_key(['school_name_clean']) }} AS school_key,    -- FK to dim_schools
    url_address,
    email_address,
    telephone_no,
    telephone_no_2,
    fax_no,
    fax_no_2,
    mrt_desc,
    bus_desc,
    principal_name,
    first_vp_name,
    second_vp_name,
    third_vp_name,
    fourth_vp_name,
    fifth_vp_name,
    sixth_vp_name

FROM {{ ref('stg_primary_schools') }}