"""
services/metadata.py

Business logic for the /metadata endpoint.

Queries dim_school for all distinct filter values used in the frontend.
Returns all schools including inactive (merged/relocated) so dropdown
values reflect the full historical dataset.

zone_code NULL (merged schools) is excluded from the zone and estate
lists — a NULL zone would appear as an empty string in the dropdown
which is confusing. Merged schools have no meaningful zone context.

Query strategy:
  Single query returning zone_code + dgp_code pairs.
  Python assembles the cascading structure — avoids multiple BigQuery
  round trips and keeps the SQL simple.
"""

from api.services.bigquery import run_query, get_dataset
from api.constants import ZONE_ORDER, NATURE_ORDER


def get_metadata() -> dict:
    """
    Fetches all distinct filter values from dim_school.

    Returns a dict ready for MetadataResponse instantiation.
    """
    dataset = get_dataset()

    sql = f"""
        SELECT DISTINCT
            zone_code,
            dgp_code,
            type_code,
            nature_code
        FROM `{dataset}.dim_school`
        WHERE zone_code IS NOT NULL AND zone_code <> 'UNKNOWN'
          AND dgp_code IS NOT NULL AND dgp_code <> 'UNKNOWN'
        ORDER BY
            zone_code ASC,
            dgp_code ASC
    """

    rows = run_query(sql)

    # zones = sorted({r["zone_code"] for r in rows if r["zone_code"]})
    zone_set = {r["zone_code"] for r in rows if r["zone_code"]}
    zones = [z for z in ZONE_ORDER if z in zone_set]
    all_estates = sorted({r["dgp_code"] for r in rows if r["dgp_code"]})
    type_codes = sorted({r["type_code"] for r in rows if r.get("type_code")})
    # nature_codes = sorted({r["nature_code"] for r in rows if r.get("nature_code")})
    nature_set = {r["nature_code"] for r in rows if r["nature_code"]}
    nature_codes = [n for n in NATURE_ORDER if n in nature_set]

    estates_by_zone: dict[str, list[str]] = {}
    for zone in zones:
        estates_by_zone[zone] = sorted(
            {r["dgp_code"] for r in rows if r["zone_code"] == zone and r["dgp_code"]}
        )

    return {
        "zones": zones,
        "estates_by_zone": estates_by_zone,
        "all_estates": all_estates,
        "type_codes": type_codes,
        "nature_codes": nature_codes,
    }
