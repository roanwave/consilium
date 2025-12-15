"""Red team chamber experts."""

from backend.experts.redteam.adversary import Adversary
from backend.experts.redteam.auditor import Auditor
from backend.experts.redteam.dramatist import Dramatist
from backend.experts.redteam.realist import Realist
from backend.experts.redteam.skeptic import Skeptic

__all__ = [
    "Adversary",
    "Auditor",
    "Dramatist",
    "Realist",
    "Skeptic",
]

# All Red Team experts in recommended review order
REDTEAM_EXPERTS = [
    Auditor,  # Math/timeline/anachronism first
    Skeptic,  # Plausibility
    Adversary,  # Enemy perspective
    Realist,  # Practical feasibility
    Dramatist,  # Narrative coherence last
]
