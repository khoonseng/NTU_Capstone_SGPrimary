select 
    {{ dbt_utils.generate_surrogate_key(['school_name_clean']) }} AS school_key
    ,*
from  {{ ref('stg_all_schools')}}