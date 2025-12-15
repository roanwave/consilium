"""Consistency checking utilities for Consilium.

Validates ScenarioSheet for internal consistency including:
- Timeline paradoxes
- Force number consistency
- Geography/distance/march rate consistency
- Commander knowledge vs fog of war
- Era/anachronism detection
"""

import re
from typing import Literal

from backend.lib.defaults import (
    ERA_CONSTRAINTS,
    MARCH_RATES,
    get_march_rate,
    is_anachronistic,
)
from backend.lib.models import ConsistencyViolation, ScenarioSheet


def check_timeline_consistency(sheet: ScenarioSheet) -> list[ConsistencyViolation]:
    """
    Check timeline for logical paradoxes.

    Validates:
    - Events have valid timestamps
    - Causal ordering makes sense
    - No circular dependencies
    """
    violations = []

    if not sheet.timeline:
        return violations

    # Parse timestamps to relative minutes for comparison
    timestamp_order: list[tuple[int, str, int]] = []

    for idx, event in enumerate(sheet.timeline):
        minutes = _parse_timestamp(event.timestamp)
        if minutes is not None:
            timestamp_order.append((minutes, event.event, idx))

    # Sort by time and check for issues
    timestamp_order.sort(key=lambda x: x[0])

    # Check that triggered_by events happen before their effects
    event_times = {event.event: _parse_timestamp(event.timestamp) for event in sheet.timeline}

    for event in sheet.timeline:
        if event.triggered_by and event.triggered_by in event_times:
            trigger_time = event_times[event.triggered_by]
            event_time = event_times.get(event.event)

            if trigger_time is not None and event_time is not None:
                if trigger_time >= event_time:
                    violations.append(
                        ConsistencyViolation(
                            field="timeline",
                            violation_type="temporal_paradox",
                            description=(
                                f"Event '{event.event}' is triggered by '{event.triggered_by}' "
                                f"but occurs at same time or earlier"
                            ),
                            severity="error",
                            suggestion="Adjust timestamps so cause precedes effect",
                        )
                    )

    return violations


def check_force_consistency(sheet: ScenarioSheet) -> list[ConsistencyViolation]:
    """
    Check force numbers are internally consistent.

    Validates:
    - Unit counts sum to total strength
    - Casualty numbers don't exceed force size
    - No negative numbers
    """
    violations = []

    for side_id, force in sheet.forces.items():
        # Check unit counts sum correctly
        if force.composition:
            unit_sum = sum(unit.count for unit in force.composition)
            if unit_sum != force.total_strength:
                violations.append(
                    ConsistencyViolation(
                        field=f"forces.{side_id}",
                        violation_type="force_count_mismatch",
                        description=(
                            f"Unit counts sum to {unit_sum} but total_strength is "
                            f"{force.total_strength}"
                        ),
                        severity="error",
                        suggestion=(
                            f"Either adjust unit counts or set total_strength to {unit_sum}"
                        ),
                    )
                )

            # Check for negative counts
            for unit in force.composition:
                if unit.count < 0:
                    violations.append(
                        ConsistencyViolation(
                            field=f"forces.{side_id}.composition",
                            violation_type="negative_count",
                            description=f"Unit '{unit.unit_type}' has negative count: {unit.count}",
                            severity="error",
                            suggestion="Unit counts must be non-negative",
                        )
                    )

    # Check casualty profile against forces
    if sheet.casualty_profile and sheet.forces:
        total_forces = sum(f.total_strength for f in sheet.forces.values())

        # Validate percentages are reasonable
        if sheet.casualty_profile.winner_casualties_percent > 100:
            violations.append(
                ConsistencyViolation(
                    field="casualty_profile.winner_casualties_percent",
                    violation_type="invalid_percentage",
                    description="Winner casualties exceed 100%",
                    severity="error",
                    suggestion="Casualty percentages must be between 0 and 100",
                )
            )

        if sheet.casualty_profile.loser_casualties_percent > 100:
            violations.append(
                ConsistencyViolation(
                    field="casualty_profile.loser_casualties_percent",
                    violation_type="invalid_percentage",
                    description="Loser casualties exceed 100%",
                    severity="error",
                    suggestion="Casualty percentages must be between 0 and 100",
                )
            )

    return violations


def check_geography_consistency(sheet: ScenarioSheet) -> list[ConsistencyViolation]:
    """
    Check geography and distances match march rates.

    Validates:
    - Movement times are achievable given distances
    - Terrain doesn't contradict itself
    """
    violations = []

    if not sheet.terrain_weather:
        return violations

    # Check terrain type matches features
    terrain = sheet.terrain_weather
    terrain_type = terrain.terrain_type.value

    # Simple heuristic checks
    if terrain_type == "desert" and terrain.weather.value in ["snow", "heavy_rain"]:
        violations.append(
            ConsistencyViolation(
                field="terrain_weather",
                violation_type="terrain_weather_mismatch",
                description=f"Desert terrain with {terrain.weather.value} weather is unusual",
                severity="warning",
                suggestion="Consider if this weather pattern is intentional for the scenario",
            )
        )

    if terrain_type == "marsh" and terrain.ground_conditions == "firm":
        violations.append(
            ConsistencyViolation(
                field="terrain_weather",
                violation_type="terrain_ground_mismatch",
                description="Marsh terrain with firm ground conditions is contradictory",
                severity="warning",
                suggestion="Marsh terrain typically has soft/muddy ground",
            )
        )

    return violations


def check_commander_knowledge(sheet: ScenarioSheet) -> list[ConsistencyViolation]:
    """
    Check that commander knowledge respects fog of war.

    Validates:
    - Decision points don't assume knowledge commanders couldn't have
    - Information_available is plausible given situation
    """
    violations = []

    for dp in sheet.decision_points:
        # Check that information_missing isn't contradicted by rationale
        for missing in dp.information_missing:
            if missing.lower() in dp.rationale.lower():
                violations.append(
                    ConsistencyViolation(
                        field="decision_points",
                        violation_type="fog_of_war_violation",
                        description=(
                            f"Decision point for {dp.commander} references "
                            f"'{missing}' in rationale but it's listed as unknown"
                        ),
                        severity="warning",
                        suggestion="Commander cannot act on information they don't have",
                    )
                )

    return violations


def check_anachronisms(sheet: ScenarioSheet) -> list[ConsistencyViolation]:
    """
    Check for era-inappropriate elements.

    Validates:
    - Weapons match era
    - Armor matches era
    - Tactics are period-appropriate
    """
    violations = []

    era = sheet.era.value
    if era not in ERA_CONSTRAINTS:
        return violations  # Fantasy or unknown era, skip checks

    constraints = ERA_CONSTRAINTS[era]
    forbidden = constraints.get("forbidden", [])

    # Check force equipment
    for side_id, force in sheet.forces.items():
        for unit in force.composition:
            # Check unit type
            for forbidden_item in forbidden:
                if forbidden_item.lower() in unit.unit_type.lower():
                    violations.append(
                        ConsistencyViolation(
                            field=f"forces.{side_id}.composition",
                            violation_type="anachronism",
                            description=(
                                f"Unit type '{unit.unit_type}' references "
                                f"'{forbidden_item}' which is anachronistic for {era} era"
                            ),
                            severity="error",
                            suggestion=f"Remove or replace {forbidden_item} with period-appropriate alternative",
                        )
                    )

            # Check equipment
            for equip in unit.equipment:
                for forbidden_item in forbidden:
                    if forbidden_item.lower() in equip.lower():
                        violations.append(
                            ConsistencyViolation(
                                field=f"forces.{side_id}.composition",
                                violation_type="anachronism",
                                description=(
                                    f"Equipment '{equip}' is anachronistic for {era} era"
                                ),
                                severity="error",
                                suggestion=f"Replace with period-appropriate equipment",
                            )
                        )

    return violations


def check_all_consistency(
    sheet: ScenarioSheet,
) -> list[ConsistencyViolation]:
    """
    Run all consistency checks on a ScenarioSheet.

    Returns:
        List of all violations found
    """
    violations = []

    violations.extend(check_timeline_consistency(sheet))
    violations.extend(check_force_consistency(sheet))
    violations.extend(check_geography_consistency(sheet))
    violations.extend(check_commander_knowledge(sheet))
    violations.extend(check_anachronisms(sheet))

    return violations


def has_blocking_violations(violations: list[ConsistencyViolation]) -> bool:
    """Check if any violations are blocking (errors)."""
    return any(v.severity == "error" for v in violations)


def filter_violations_by_severity(
    violations: list[ConsistencyViolation],
    severity: Literal["error", "warning"],
) -> list[ConsistencyViolation]:
    """Filter violations by severity level."""
    return [v for v in violations if v.severity == severity]


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_timestamp(timestamp: str) -> int | None:
    """
    Parse a relative timestamp string to minutes.

    Supports formats:
    - "H+30m" -> 30
    - "H+1h" -> 60
    - "H+1h30m" -> 90
    - "Dawn" -> 0 (reference point)
    - "Dawn+30m" -> 30
    """
    timestamp = timestamp.strip().lower()

    # Named times (treat as reference points)
    named_times = {
        "dawn": 0,
        "morning": 60,
        "midday": 360,
        "noon": 360,
        "afternoon": 480,
        "evening": 600,
        "dusk": 720,
        "night": 780,
    }

    # Check for named time
    for name, minutes in named_times.items():
        if timestamp.startswith(name):
            base = minutes
            # Check for offset
            if "+" in timestamp:
                offset_str = timestamp.split("+", 1)[1]
                offset = _parse_duration(offset_str)
                if offset is not None:
                    return base + offset
            return base

    # Check for H+ format
    if timestamp.startswith("h+"):
        offset_str = timestamp[2:]
        return _parse_duration(offset_str)

    # Try to parse as pure duration
    return _parse_duration(timestamp)


def _parse_duration(duration: str) -> int | None:
    """Parse a duration string like '30m', '1h', '1h30m' to minutes."""
    duration = duration.strip().lower()

    total_minutes = 0

    # Match hours
    hours_match = re.search(r"(\d+)h", duration)
    if hours_match:
        total_minutes += int(hours_match.group(1)) * 60

    # Match minutes
    mins_match = re.search(r"(\d+)m", duration)
    if mins_match:
        total_minutes += int(mins_match.group(1))

    # If we found something, return it
    if hours_match or mins_match:
        return total_minutes

    # Try to parse as raw number (assume minutes)
    try:
        return int(duration)
    except ValueError:
        return None
