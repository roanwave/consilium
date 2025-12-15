"""Consilium chamber experts."""

from backend.experts.consilium.armorer import Armorer
from backend.experts.consilium.chronicler import Chronicler
from backend.experts.consilium.commander import Commander
from backend.experts.consilium.geographer import Geographer
from backend.experts.consilium.herald import Herald
from backend.experts.consilium.logistician import Logistician
from backend.experts.consilium.strategist import Strategist
from backend.experts.consilium.surgeon import Surgeon
from backend.experts.consilium.tactician import Tactician

__all__ = [
    "Armorer",
    "Chronicler",
    "Commander",
    "Geographer",
    "Herald",
    "Logistician",
    "Strategist",
    "Surgeon",
    "Tactician",
]

# All Consilium experts in recommended consultation order
CONSILIUM_EXPERTS = [
    Strategist,
    Tactician,
    Logistician,
    Geographer,
    Armorer,
    Surgeon,
    Commander,
    Chronicler,
    Herald,
]
