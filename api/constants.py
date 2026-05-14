"""
constants.py

Shared constants used across the SGPrimary API.

Centralised here following the DRY principle — any change to valid
phases, risk levels, or other domain constants is made once here
and takes effect across all routers and services automatically.
"""

# Valid phases for ballot prediction and recommendation endpoints.
# Phases 1 and 2A are excluded — they are priority phases with
# guaranteed or semi-guaranteed entry and are not in scope for
# ballot difficulty analysis in this iteration.
VALID_PHASES = {"2B", "2C", "2C(S)", "3"}