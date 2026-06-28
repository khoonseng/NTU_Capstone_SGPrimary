"""Shared event schema for the p1_vacancy_snapshots Kafka topic.

Used by both producer and consumer so the message shape is defined once.

Kafka message flow:
  vacancy_producer.py  →  Kafka topic: p1_vacancy_snapshots  →  vacancy_consumer.py
        produces VacancySnapshot.to_dict()          deserialises with VacancySnapshot.from_dict()

BigQuery target table: sg_moe.raw_p1_vacancy_snapshots
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


@dataclass
class VacancySnapshot:
    event_id: str                              # UUID, unique per snapshot
    phase: str                                 # e.g. "2B", "2C", "2C(S)"
    registration_year: int                     # e.g. 2026
    school_name: str                           # canonical name from dim_school
    snapshot_timestamp: str                    # ISO 8601 with SGT offset, e.g. "2026-07-28T12:00:00+08:00"
    snapshot_type: Literal["midday", "end_of_day"]
    vacancy_at_open: int                       # total vacancies at phase start (seeded from historical)
    vacancy_remaining: int                     # simulated remaining vacancies at snapshot time
    applied_count: int                         # simulated cumulative applicants at snapshot time
    pct_filled: float                          # (vacancy_at_open - vacancy_remaining) / vacancy_at_open
    simulation_day: int                        # 1, 2, or 3 (day within the 3-day registration window)

    def to_dict(self) -> dict:
        """Serialise to a plain dict for JSON encoding before publishing to Kafka."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> VacancySnapshot:
        """Deserialise from a plain dict after reading from Kafka."""
        return cls(**data)
