"""Baseline defaults tables for Consilium.

These tables codify reasonable defaults so the system stays internally consistent.
Values are based on historical military data and academic sources.
"""

from typing import TypeAlias

# Type aliases for clarity
RangeTuple: TypeAlias = tuple[float, float]  # (min, max)


# =============================================================================
# March Rates (km/day)
# =============================================================================

MARCH_RATES: dict[str, RangeTuple] = {
    # Infantry
    "foot_light": (20, 25),  # Light infantry, skirmishers
    "foot_heavy": (12, 18),  # Heavy infantry with armor
    "foot_mixed": (15, 20),  # Mixed infantry column

    # Cavalry
    "cavalry_light": (35, 50),  # Light cavalry, scouts
    "cavalry_heavy": (25, 35),  # Heavy cavalry, knights
    "cavalry_pursuit": (40, 60),  # Pursuit pace (unsustainable)

    # Combined arms
    "mixed_army": (15, 20),  # Combined arms force
    "baggage_heavy": (8, 12),  # Army with heavy baggage train

    # Special conditions
    "forced_march": (30, 40),  # Sustainable 1-2 days max, then exhaustion
    "mountain_terrain": (8, 12),  # Reduced for difficult terrain
    "forest_terrain": (10, 15),  # Reduced for wooded terrain
    "mud_conditions": (6, 10),  # Heavily reduced for mud/rain
}


# =============================================================================
# Frontage (meters per combatant)
# =============================================================================

FRONTAGE: dict[str, float] = {
    # Infantry formations
    "close_order_foot": 0.7,  # Shoulder to shoulder
    "loose_order_foot": 1.5,  # Skirmish/flexible
    "pike_formation": 0.5,  # Dense pike square
    "phalanx": 0.5,  # Classical phalanx
    "shield_wall": 0.6,  # Anglo-Saxon/Viking shield wall
    "testudo": 0.5,  # Roman tortoise

    # Cavalry
    "cavalry_line": 1.2,  # Mounted line
    "cavalry_wedge": 1.0,  # Wedge formation
    "cavalry_column": 0.8,  # Column for movement

    # Ranged
    "archers_loose": 2.0,  # Archers need room to draw
    "crossbow": 1.5,  # Crossbowmen
    "slingers": 2.5,  # Slingers need more room

    # Artillery (per piece)
    "catapult": 8.0,  # Siege engine frontage
    "ballista": 4.0,  # Bolt thrower
    "trebuchet": 12.0,  # Large siege engine
}


# =============================================================================
# Casualty Ratios (fraction of force)
# =============================================================================

CASUALTY_RATIOS: dict[str, RangeTuple] = {
    # Winner casualties
    "decisive_victory": (0.05, 0.15),  # Clean win
    "pyrrhic_victory": (0.20, 0.35),  # Costly win
    "narrow_victory": (0.10, 0.20),  # Close fight

    # Mutual casualties
    "stalemate": (0.10, 0.20),  # Both sides roughly equal
    "mutual_exhaustion": (0.15, 0.25),  # Both sides fought to standstill

    # Loser casualties
    "fighting_retreat": (0.15, 0.25),  # Organized withdrawal
    "rout": (0.30, 0.60),  # Complete collapse
    "encirclement": (0.50, 0.90),  # Surrounded force

    # Special cases
    "siege_assault": (0.20, 0.40),  # Attacker in siege assault
    "siege_defense": (0.10, 0.25),  # Defender in siege assault
    "ambush_victim": (0.25, 0.50),  # Ambushed force
}


# =============================================================================
# Message Latency
# =============================================================================

MESSAGE_LATENCY: dict[str, float] = {
    # Speed per km
    "mounted_courier_km": 2,  # Minutes per km
    "runner_km": 6,  # Minutes per km
    "relay_runner_km": 4,  # Fresh runners in relay

    # Fixed times
    "signal_flag_visible": 0.5,  # Minutes if in line of sight
    "horn_audible_km": 1,  # Effective range in km
    "drum_audible_km": 0.5,  # Effective range in km
    "smoke_signal_km": 5,  # Visible range in km (clear day)

    # Delays
    "interpret_signal": 1,  # Minutes to interpret signal
    "compose_written_order": 5,  # Minutes to write order
    "verbal_briefing": 2,  # Minutes for verbal order
}


# =============================================================================
# Endurance Limits
# =============================================================================

ENDURANCE: dict[str, RangeTuple] = {
    # Combat duration
    "intense_melee_minutes": (5, 15),  # Hand-to-hand fighting
    "sustained_combat_hours": (1, 3),  # Prolonged engagement
    "skirmish_hours": (2, 6),  # Light contact
    "siege_days": (14, 180),  # Siege duration

    # Physical limits
    "pursuit_before_exhaustion_km": (3, 8),  # Pursuit distance
    "charge_distance_meters": (100, 300),  # Cavalry charge
    "sprint_meters": (100, 200),  # Infantry sprint

    # Activity windows
    "time_in_armor_hours": (4, 8),  # Heavy armor wear time
    "march_before_rest_hours": (6, 10),  # Continuous march
    "battle_readiness_hours": (12, 18),  # After forced march
}


# =============================================================================
# Era Constraints (Anachronism Detection)
# =============================================================================

ERA_CONSTRAINTS: dict[str, dict[str, list[str]]] = {
    "ancient": {
        "allowed_weapons": [
            "sword", "spear", "javelin", "bow", "sling", "dagger",
            "axe", "mace", "pike", "sarissa", "gladius", "pilum",
        ],
        "allowed_armor": [
            "leather", "linen", "bronze", "iron", "mail", "scale",
            "lorica segmentata", "linothorax", "muscle cuirass",
        ],
        "forbidden": [
            "crossbow", "plate armor", "longbow", "gunpowder", "cannon",
            "pike and shot", "musket", "arquebus", "stirrups",
        ],
        "notes": "Pre-500 CE. No stirrups until late period.",
    },
    "early_medieval": {
        "allowed_weapons": [
            "sword", "spear", "axe", "bow", "seax", "francisca",
            "scramasax", "lance", "javelin", "mace", "flail",
        ],
        "allowed_armor": [
            "mail", "scale", "leather", "gambeson", "helm", "shield",
            "lamellar",
        ],
        "forbidden": [
            "plate armor", "longbow", "crossbow (early)", "gunpowder",
            "full plate", "tournament armor",
        ],
        "notes": "500-1000 CE. Stirrups arrive mid-period. Limited crossbow.",
    },
    "high_medieval": {
        "allowed_weapons": [
            "sword", "lance", "mace", "flail", "crossbow", "longbow",
            "poleaxe", "halberd", "morning star", "war hammer",
        ],
        "allowed_armor": [
            "mail", "coat of plates", "early plate", "great helm",
            "gambeson", "surcoat",
        ],
        "forbidden": [
            "gunpowder", "cannon", "arquebus", "musket", "full plate",
        ],
        "notes": "1000-1300 CE. Crossbow common. Plate developing.",
    },
    "late_medieval": {
        "allowed_weapons": [
            "sword", "lance", "poleaxe", "longbow", "crossbow",
            "early cannon", "hand cannon", "pike", "bill", "halberd",
        ],
        "allowed_armor": [
            "full plate", "brigandine", "mail", "sallet", "armet",
            "tournament armor",
        ],
        "forbidden": [
            "musket", "arquebus (late only)", "rifle", "bayonet",
        ],
        "notes": "1300-1500 CE. Gunpowder emerges. Full plate common.",
    },
    "renaissance": {
        "allowed_weapons": [
            "pike", "arquebus", "sword", "rapier", "halberd",
            "cannon", "musket", "pistol", "lance",
        ],
        "allowed_armor": [
            "plate", "morion", "burgonet", "cuirass", "buff coat",
        ],
        "forbidden": [
            "rifle", "bayonet", "flintlock",
        ],
        "notes": "1500-1600 CE. Pike and shot era. Cavalry transitioning.",
    },
    "fantasy": {
        "allowed_weapons": ["any"],
        "allowed_armor": ["any"],
        "forbidden": [],
        "notes": "Fantasy settings allow anachronisms if internally consistent.",
    },
}


# =============================================================================
# Formation Depths
# =============================================================================

FORMATION_DEPTH: dict[str, int] = {
    # Infantry
    "phalanx": 8,  # Traditional Greek phalanx
    "macedonian_phalanx": 16,  # Deeper Macedonian style
    "roman_triplex": 3,  # Three lines
    "shield_wall": 4,  # 3-5 ranks typical
    "pike_square": 10,  # Renaissance pike block

    # Cavalry
    "cavalry_line": 2,  # Two ranks typical
    "cavalry_wedge": 5,  # Wedge depth
    "cavalry_column": 10,  # Movement column
}


# =============================================================================
# Morale Thresholds
# =============================================================================

MORALE_THRESHOLDS: dict[str, float] = {
    "rout_trigger": 0.25,  # Casualties that trigger rout (fraction)
    "waver_trigger": 0.15,  # Casualties that cause wavering
    "elite_bonus": 0.10,  # Additional casualties elite units absorb
    "green_penalty": -0.05,  # Earlier break for green troops
    "flanked_modifier": -0.10,  # Earlier break when flanked
    "leader_killed": -0.15,  # Morale hit when leader killed
    "leader_rallying": 0.05,  # Morale recovery with leader present
}


# =============================================================================
# Visibility Ranges (meters)
# =============================================================================

VISIBILITY: dict[str, RangeTuple] = {
    "clear_day": (5000, 10000),  # Unlimited practical visibility
    "overcast": (3000, 5000),  # Reduced but adequate
    "rain": (500, 1500),  # Significantly reduced
    "heavy_rain": (100, 500),  # Severely limited
    "fog": (50, 200),  # Very limited
    "night_clear": (50, 100),  # By moonlight
    "night_dark": (10, 30),  # Near blind
    "dust_cloud": (100, 500),  # Battle dust
    "smoke": (50, 200),  # Fire/siege smoke
}


# =============================================================================
# Supply Consumption (per 1000 men per day)
# =============================================================================

SUPPLY_CONSUMPTION: dict[str, float] = {
    "food_kg": 1500,  # Food in kg
    "water_liters": 3000,  # Water in liters
    "fodder_kg": 5000,  # Horse fodder per 1000 horses
    "arrows_volleys": 100,  # Arrow consumption in volleys
    "bolts_volleys": 50,  # Crossbow bolts
}


# =============================================================================
# Helper Functions
# =============================================================================


def get_march_rate(unit_type: str, conditions: str = "normal") -> RangeTuple:
    """Get march rate for unit type with conditions modifier."""
    base = MARCH_RATES.get(unit_type, MARCH_RATES["mixed_army"])
    if conditions == "mud":
        return MARCH_RATES["mud_conditions"]
    if conditions == "mountain":
        return MARCH_RATES["mountain_terrain"]
    if conditions == "forest":
        return MARCH_RATES["forest_terrain"]
    return base


def get_casualty_range(outcome: str) -> RangeTuple:
    """Get casualty range for battle outcome."""
    return CASUALTY_RATIOS.get(outcome, (0.10, 0.20))


def calculate_frontage(unit_type: str, count: int) -> float:
    """Calculate frontage in meters for a unit."""
    per_man = FRONTAGE.get(unit_type, FRONTAGE["loose_order_foot"])
    return count * per_man


def is_anachronistic(era: str, item: str, item_type: str = "weapons") -> bool:
    """Check if an item is anachronistic for an era."""
    if era not in ERA_CONSTRAINTS:
        return False
    constraints = ERA_CONSTRAINTS[era]
    if item_type == "weapons":
        forbidden = constraints.get("forbidden", [])
        return any(f.lower() in item.lower() for f in forbidden)
    return False


def get_message_time(distance_km: float, method: str = "mounted_courier") -> float:
    """Calculate message delivery time in minutes."""
    rate_key = f"{method}_km"
    rate = MESSAGE_LATENCY.get(rate_key, MESSAGE_LATENCY["runner_km"])
    base_time = distance_km * rate
    # Add interpretation delay
    return base_time + MESSAGE_LATENCY["interpret_signal"]


def get_combat_duration(intensity: str = "sustained") -> RangeTuple:
    """Get expected combat duration."""
    if intensity == "intense":
        return ENDURANCE["intense_melee_minutes"]
    if intensity == "skirmish":
        return ENDURANCE["skirmish_hours"]
    return ENDURANCE["sustained_combat_hours"]
