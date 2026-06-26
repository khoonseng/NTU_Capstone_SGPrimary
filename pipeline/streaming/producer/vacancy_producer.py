"""Kafka producer for P1 vacancy snapshot events.

Publishes synthetic vacancy snapshots to the p1_vacancy_snapshots Kafka topic.
Events are seeded from mart_school_analysis historical figures and apply a
realistic drift curve across a simulated 3-day registration window.

Usage:
    python vacancy_producer.py --mode replay   --phase 2C  --year 2026
    python vacancy_producer.py --mode realtime --phase 2C  --year 2026

Modes:
    replay    Emit all 6 snapshot slots immediately (demo / testing).
    realtime  Emit one slot at a time, sleeping until the next scheduled
              noon or 6pm SGT window (meant for actual registration days).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from confluent_kafka import Producer
from dotenv import load_dotenv

# schemas/ is one level up from producer/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from schemas.vacancy_snapshot import VacancySnapshot
from seed_data import fetch_seed_data

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = "p1_vacancy_snapshots"
SGT = timezone(timedelta(hours=8))

# 6 snapshot slots across the 3-day registration window.
# Each tuple: (simulation_day, snapshot_type, pct_of_final_applied_count)
# pct_of_final mirrors realistic parent registration behaviour:
# most parents register in the first two days, trailing off by day 3.
DRIFT_SCHEDULE = [
    (1, "midday",     0.35),
    (1, "end_of_day", 0.55),
    (2, "midday",     0.75),
    (2, "end_of_day", 0.87),
    (3, "midday",     0.95),
    (3, "end_of_day", 1.00),
]

# Registration window start dates (year → phase → ISO date string).
# Add future years here as MOE publishes the P1 registration calendar.
PHASE_WINDOW_START: dict[int, dict[str, str]] = {
    2026: {
        "2B":    "2026-07-24",   # 3-day window closes before results on 27 Jul
        "2C":    "2026-08-08",   # 3-day window closes before results on 11 Aug
        "2C(S)": "2026-08-24",   # 3-day window closes before results on 27 Aug
    },
}

REPLAY_INTER_MESSAGE_SLEEP = 0.05  # seconds between messages in replay mode


def delivery_report(err, msg) -> None:
    """Print Kafka delivery result after the broker accepts or rejects a message."""
    if err is not None:
        print(f"  Delivery failed: {err}", flush=True)
        return
    print(
        f"  Delivered key={msg.key().decode()} "
        f"partition={msg.partition()} offset={msg.offset()}",
        flush=True,
    )


def _make_timestamp(phase_start: str, simulation_day: int, snapshot_type: str) -> str:
    """Return an ISO 8601 SGT timestamp for the given simulation slot."""
    start = datetime.strptime(phase_start, "%Y-%m-%d")
    target = start + timedelta(days=simulation_day - 1)
    hour = 12 if snapshot_type == "midday" else 18
    return datetime(target.year, target.month, target.day, hour, 0, 0, tzinfo=SGT).isoformat()


def _build_snapshot(seed: dict, phase_start: str, year: int,
                    simulation_day: int, snapshot_type: str, pct: float) -> VacancySnapshot:
    """Build one VacancySnapshot from seed data and a drift percentage."""
    vacancy_at_open   = seed["vacancy_at_open"]
    final_applied     = seed["final_applied_count"] or 0

    applied_count     = round(final_applied * pct)
    vacancy_remaining = max(0, vacancy_at_open - applied_count)
    pct_filled        = round(
        (vacancy_at_open - vacancy_remaining) / vacancy_at_open, 4
    ) if vacancy_at_open > 0 else 0.0

    return VacancySnapshot(
        event_id           = str(uuid.uuid4()),
        phase              = seed["phase"],
        registration_year  = year,
        school_name        = seed["school_name"],
        snapshot_timestamp = _make_timestamp(phase_start, simulation_day, snapshot_type),
        snapshot_type      = snapshot_type,
        vacancy_at_open    = vacancy_at_open,
        vacancy_remaining  = vacancy_remaining,
        applied_count      = applied_count,
        pct_filled         = pct_filled,
        simulation_day     = simulation_day,
    )


def _publish_slot(producer: Producer, seeds: list[dict], phase_start: str,
                  year: int, simulation_day: int, snapshot_type: str, pct: float,
                  inter_sleep: float = 0.0) -> int:
    """Emit one snapshot per school for a single time slot. Returns message count."""
    count = 0
    for seed in seeds:
        snapshot = _build_snapshot(seed, phase_start, year, simulation_day, snapshot_type, pct)
        producer.produce(
            topic    = TOPIC,
            key      = f"{snapshot.school_name}_{snapshot.phase}".encode("utf-8"),
            value    = json.dumps(snapshot.to_dict()).encode("utf-8"),
            callback = delivery_report,
        )
        producer.poll(0)
        count += 1
        if inter_sleep:
            time.sleep(inter_sleep)
    producer.flush()
    return count


def run_replay(producer: Producer, seeds: list[dict], phase: str, year: int) -> None:
    """Emit all 6 snapshot slots immediately."""
    phase_start = PHASE_WINDOW_START.get(year, {}).get(phase)
    if not phase_start:
        print(
            f"No phase window defined for year={year} phase={phase}.\n"
            f"Add an entry to PHASE_WINDOW_START in vacancy_producer.py.",
            file=sys.stderr,
        )
        sys.exit(1)

    total = 0
    for sim_day, snap_type, pct in DRIFT_SCHEDULE:
        print(f"\n--- Day {sim_day} {snap_type} ({int(pct * 100)}%) ---", flush=True)
        n = _publish_slot(producer, seeds, phase_start, year,
                          sim_day, snap_type, pct, REPLAY_INTER_MESSAGE_SLEEP)
        total += n
        print(f"  {n} messages published.", flush=True)

    print(f"\nReplay complete — {total} total messages on topic {TOPIC}.", flush=True)


def run_realtime(producer: Producer, seeds: list[dict], phase: str, year: int) -> None:
    """Emit one slot at the correct SGT time, sleeping between slots."""
    phase_start = PHASE_WINDOW_START.get(year, {}).get(phase)
    if not phase_start:
        print(
            f"No phase window defined for year={year} phase={phase}.\n"
            f"Add an entry to PHASE_WINDOW_START in vacancy_producer.py.",
            file=sys.stderr,
        )
        sys.exit(1)

    for sim_day, snap_type, pct in DRIFT_SCHEDULE:
        target_ts = _make_timestamp(phase_start, sim_day, snap_type)
        target_dt = datetime.fromisoformat(target_ts)
        wait_secs = (target_dt - datetime.now(tz=SGT)).total_seconds()

        if wait_secs > 0:
            print(
                f"Waiting {wait_secs / 3600:.1f}h until {target_ts} "
                f"(Day {sim_day} {snap_type})...",
                flush=True,
            )
            time.sleep(wait_secs)

        print(f"\n--- Day {sim_day} {snap_type} ({int(pct * 100)}%) ---", flush=True)
        n = _publish_slot(producer, seeds, phase_start, year, sim_day, snap_type, pct)
        print(f"  {n} messages published.", flush=True)

    print(f"\nRealtime run complete — phase {phase} {year}.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SGPrimary P1 vacancy snapshot Kafka producer"
    )
    parser.add_argument(
        "--mode", required=True, choices=["replay", "realtime"],
        help="replay: emit all slots immediately; realtime: wait for noon/6pm SGT",
    )
    parser.add_argument(
        "--phase", required=True, choices=["2B", "2C", "2C(S)"],
        help="Registration phase to simulate",
    )
    parser.add_argument(
        "--year", type=int, default=datetime.now(tz=SGT).year,
        help="Registration year (default: current SGT year)",
    )
    args = parser.parse_args()

    print(
        f"SGPrimary vacancy producer  mode={args.mode}  "
        f"phase={args.phase}  year={args.year}",
        flush=True,
    )
    print(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS}  topic: {TOPIC}\n", flush=True)

    seeds = fetch_seed_data()
    if not seeds:
        print("No seed data from BigQuery. Exiting.", file=sys.stderr)
        sys.exit(1)

    phase_seeds = [s for s in seeds if s["phase"] == args.phase]
    if not phase_seeds:
        print(f"No seed records for phase {args.phase}. Exiting.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(phase_seeds)} schools for phase {args.phase}.", flush=True)

    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})

    if args.mode == "replay":
        run_replay(producer, phase_seeds, args.phase, args.year)
    else:
        run_realtime(producer, phase_seeds, args.phase, args.year)


if __name__ == "__main__":
    main()
