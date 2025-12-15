"""Pydantic models for Consilium."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class Era(str, Enum):
    """Historical era for the battle."""

    ANCIENT = "ancient"  # Pre-500 CE
    EARLY_MEDIEVAL = "early_medieval"  # 500-1000 CE
    HIGH_MEDIEVAL = "high_medieval"  # 1000-1300 CE
    LATE_MEDIEVAL = "late_medieval"  # 1300-1500 CE
    RENAISSANCE = "renaissance"  # 1500-1600 CE
    FANTASY = "fantasy"  # Ahistorical


class TerrainType(str, Enum):
    """Primary terrain type."""

    PLAINS = "plains"
    HILLS = "hills"
    MOUNTAINS = "mountains"
    FOREST = "forest"
    MARSH = "marsh"
    RIVER_CROSSING = "river_crossing"
    COASTAL = "coastal"
    URBAN = "urban"
    DESERT = "desert"


class WeatherCondition(str, Enum):
    """Weather conditions."""

    CLEAR = "clear"
    OVERCAST = "overcast"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    FOG = "fog"
    SNOW = "snow"
    MUD = "mud"  # Post-rain conditions


class ViolenceLevel(str, Enum):
    """Violence detail level for output."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CommanderCompetence(str, Enum):
    """Commander skill level."""

    INCOMPETENT = "incompetent"
    MEDIOCRE = "mediocre"
    COMPETENT = "competent"
    SKILLED = "skilled"
    BRILLIANT = "brilliant"


class NarrativeOutcome(str, Enum):
    """Desired battle outcome."""

    DECISIVE_VICTORY = "decisive_victory"
    PYRRHIC_VICTORY = "pyrrhic_victory"
    STALEMATE = "stalemate"
    FIGHTING_RETREAT = "fighting_retreat"
    ROUT = "rout"
    OTHER = "other"


class ObjectionType(str, Enum):
    """Type of red team objection."""

    STRUCTURAL = "structural"  # Requires scenario rewrite
    REFINABLE = "refinable"  # Can be addressed in next round
    COSMETIC = "cosmetic"  # Minor wording issues
    DISMISSED = "dismissed"  # Not valid objection


class DeltaOperation(str, Enum):
    """Type of delta operation."""

    SET = "set"  # Replace field entirely
    APPEND = "append"  # Add to list field
    MODIFY = "modify"  # Partial modification


class Chamber(str, Enum):
    """Expert chamber."""

    CONSILIUM = "consilium"
    REDTEAM = "redteam"


class SessionStatus(str, Enum):
    """Session lifecycle status."""

    CREATED = "created"
    INTERROGATING = "interrogating"
    DELIBERATING = "deliberating"
    CERTIFIED = "certified"
    FAILED = "failed"


# =============================================================================
# ScenarioSheet Components
# =============================================================================


class UnitComposition(BaseModel):
    """Composition of a military unit."""

    unit_type: str = Field(description="Type of unit (e.g., 'heavy cavalry', 'pike')")
    count: int = Field(ge=0, description="Number of troops")
    quality: str = Field(description="Unit quality/training level")
    equipment: list[str] = Field(default_factory=list, description="Notable equipment")
    notes: str = Field(default="", description="Additional notes")


class Commander(BaseModel):
    """Commander information."""

    name: str = Field(description="Commander name")
    title: str = Field(default="", description="Title or rank")
    competence: CommanderCompetence = Field(description="Skill level")
    personality_traits: list[str] = Field(
        default_factory=list, description="Relevant personality traits"
    )
    known_for: str = Field(default="", description="What they're known for")

    @property
    def notable_traits(self) -> list[str]:
        """Alias for personality_traits for backward compatibility."""
        return self.personality_traits


class ForceDescription(BaseModel):
    """Description of one side's forces."""

    side_name: str = Field(description="Name/identifier for this side")
    total_strength: int = Field(ge=0, description="Total troop count")
    composition: list[UnitComposition] = Field(
        default_factory=list, description="Unit breakdown"
    )
    commander: Commander = Field(description="Commanding officer")
    sub_commanders: list[Commander] = Field(
        default_factory=list, description="Subordinate commanders"
    )
    morale: str = Field(default="steady", description="Overall morale state")
    morale_factors: list[str] = Field(
        default_factory=list, description="Factors affecting morale"
    )
    supply_state: str = Field(default="adequate", description="Supply situation")
    equipment: str | None = Field(default=None, description="Equipment description")
    armor_quality: str | None = Field(default=None, description="Armor quality assessment")
    objectives: list[str] = Field(default_factory=list, description="Strategic objectives")
    constraints: list[str] = Field(
        default_factory=list, description="Operational constraints"
    )


class TerrainFeature(BaseModel):
    """A notable terrain feature."""

    name: str = Field(description="Feature name")
    description: str = Field(description="Feature description")
    tactical_impact: str = Field(description="How it affects battle")


class TerrainWeather(BaseModel):
    """Terrain and weather conditions."""

    terrain_type: TerrainType = Field(description="Primary terrain")
    defining_feature: str = Field(description="The one defining terrain feature")
    features: list[TerrainFeature] = Field(
        default_factory=list, description="Notable features"
    )
    weather: WeatherCondition = Field(default=WeatherCondition.CLEAR)
    visibility: str = Field(default="good", description="Visibility conditions")
    ground_conditions: str = Field(default="firm", description="Ground state")
    time_of_day: str = Field(default="morning", description="Time of engagement")
    season: str = Field(default="summer", description="Season")
    what_matters: list[str] = Field(
        default_factory=list, description="Terrain factors that matter"
    )
    what_doesnt: list[str] = Field(
        default_factory=list, description="Terrain factors that don't matter"
    )


class TimelineEvent(BaseModel):
    """An event in the battle timeline."""

    timestamp: str = Field(description="Relative timestamp (e.g., 'H+30m', 'Dawn')")
    event: str = Field(description="What happens")
    triggered_by: str = Field(default="", description="What caused this event")
    consequences: list[str] = Field(default_factory=list, description="Immediate effects")
    fog_of_war: str = Field(default="", description="What commanders don't know")


class DecisionPoint(BaseModel):
    """A point where commanders must choose under uncertainty."""

    timestamp: str = Field(description="When this decision occurs")
    commander: str = Field(description="Who must decide")
    situation: str = Field(description="The situation faced")
    options: list[str] = Field(description="Available choices")
    chosen: str = Field(default="", description="What was chosen")
    rationale: str = Field(default="", description="Why this choice")
    consequences: str = Field(default="", description="What resulted")
    information_available: list[str] = Field(
        default_factory=list, description="What the commander knew"
    )
    information_missing: list[str] = Field(
        default_factory=list, description="What they didn't know"
    )


class CasualtyProfile(BaseModel):
    """Casualty and attrition pattern."""

    winner_casualties_percent: float = Field(
        ge=0, le=100, description="Winner casualties as percentage"
    )
    loser_casualties_percent: float = Field(
        ge=0, le=100, description="Loser casualties as percentage"
    )
    casualty_distribution: str = Field(
        default="", description="How casualties distributed across units"
    )
    notable_deaths: list[str] = Field(
        default_factory=list, description="Notable casualties"
    )
    medical_notes: str = Field(default="", description="Medical/injury patterns")
    prisoners: str = Field(default="", description="Prisoner situation")
    pursuit_casualties: str = Field(default="", description="Casualties during pursuit/rout")


class MagicSystem(BaseModel):
    """Magic system constraints if magic is present."""

    present: bool = Field(default=False, description="Is magic present?")
    constraints: list[str] = Field(
        default_factory=list, description="Constraints on magic use"
    )
    practitioners: list[str] = Field(
        default_factory=list, description="Who can use magic"
    )
    tactical_role: str = Field(default="", description="How magic affects tactics")


# =============================================================================
# ScenarioSheet - The Canonical State Object
# =============================================================================


class ScenarioSheet(BaseModel):
    """
    The canonical state object. Moderator owns this; experts propose deltas.
    """

    version: int = Field(default=0, description="Increments on each certified change")

    # Core fields
    era: Era = Field(description="Historical era")
    theater: str = Field(default="", description="Geographic region/theater")
    stakes: str = Field(description="Why this battle happens")
    constraints: list[str] = Field(
        default_factory=list, description="Political/logistical/terrain constraints"
    )
    forces: dict[str, ForceDescription] = Field(
        default_factory=dict, description="Forces keyed by side identifier"
    )
    terrain_weather: TerrainWeather | None = Field(
        default=None, description="Terrain and weather"
    )
    timeline: list[TimelineEvent] = Field(
        default_factory=list, description="Anchor events with timestamps"
    )
    decision_points: list[DecisionPoint] = Field(
        default_factory=list, description="Where commanders choose under uncertainty"
    )
    casualty_profile: CasualtyProfile | None = Field(
        default=None, description="Plausible injury/attrition pattern"
    )
    aftermath: str = Field(default="", description="Immediate campaign consequence")
    open_risks: list[str] = Field(
        default_factory=list, description="Known vulnerabilities accepted by commanders"
    )
    magic: MagicSystem = Field(
        default_factory=MagicSystem, description="Magic system if present"
    )

    # Metadata
    last_modified_by: str = Field(default="system", description="Expert codename or 'moderator'")
    consistency_hash: str = Field(default="", description="For SSE state tracking")

    def increment_version(self, modified_by: str) -> None:
        """Increment version and update metadata."""
        self.version += 1
        self.last_modified_by = modified_by
        self.consistency_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute a hash for state tracking."""
        import hashlib

        content = self.model_dump_json(exclude={"consistency_hash"})
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# Expert Contribution Models
# =============================================================================


class DeltaRequest(BaseModel):
    """A proposed edit to the ScenarioSheet."""

    field: str = Field(description="ScenarioSheet field name (dot notation for nested)")
    operation: DeltaOperation = Field(description="Type of operation")
    value: Any = Field(description="New value or modification")
    rationale: str = Field(description="Why this change")


class ExpertContribution(BaseModel):
    """Structured output from an expert."""

    expert: str = Field(description="Expert codename")
    domain_claims: list[str] = Field(description="Bullet claims strictly in-domain")
    assumptions: list[str] = Field(
        default_factory=list, description="What they assumed because unknown"
    )
    questions_remaining: list[str] = Field(
        default_factory=list, description="What they still need answered"
    )
    delta_requests: list[DeltaRequest] = Field(
        default_factory=list, description="Proposed edits to ScenarioSheet"
    )
    narrative_fragment: str = Field(
        default="", description="Optional prose for final output"
    )


class RedTeamObjection(BaseModel):
    """An objection from a red team expert."""

    expert: str = Field(description="Expert codename")
    target: str = Field(description="What is being objected to")
    objection: str = Field(description="The objection")
    severity: str = Field(description="How serious")
    suggestion: str = Field(default="", description="Suggested fix")


class FilteredObjection(BaseModel):
    """An objection after moderator filtering."""

    original: RedTeamObjection = Field(description="Original objection")
    objection_type: ObjectionType = Field(description="Classification")
    moderator_notes: str = Field(default="", description="Moderator's reasoning")
    action_required: str = Field(default="", description="What needs to happen")


# =============================================================================
# Interrogation Models
# =============================================================================


class CoreInterrogation(BaseModel):
    """The 8 core system questions."""

    era: Era = Field(description="Era + theater")
    theater: str = Field(default="", description="Geographic theater")
    why_battle_now: str = Field(description="What forces the engagement?")
    army_sizes: str = Field(description="Army sizes + key asymmetry")
    terrain_type: TerrainType = Field(description="Terrain type")
    terrain_feature: str = Field(description="One defining feature")
    commander_competence_side_a: CommanderCompetence = Field(description="Side A commander")
    commander_competence_side_b: CommanderCompetence = Field(description="Side B commander")
    magic_present: bool = Field(default=False, description="Is magic present?")
    magic_constraints: str = Field(default="", description="Magic constraints if yes")
    narrative_outcome: NarrativeOutcome = Field(description="Desired outcome")
    violence_level: ViolenceLevel = Field(
        default=ViolenceLevel.MEDIUM, description="Violence detail level"
    )


class ExpertQuestion(BaseModel):
    """A conditional question from an expert."""

    expert: str = Field(description="Expert codename")
    question: str = Field(description="The question")
    context: str = Field(default="", description="Why this is needed")
    default: str = Field(default="", description="Default if not answered")


class ExpertInterrogation(BaseModel):
    """Conditional questions from experts."""

    questions: list[ExpertQuestion] = Field(
        default_factory=list, description="Expert questions"
    )
    answers: dict[str, str] = Field(
        default_factory=dict, description="Answers keyed by expert codename"
    )


# =============================================================================
# SSE Event Models
# =============================================================================


class TokenUsage(BaseModel):
    """Token usage tracking."""

    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cache_read_tokens: int = Field(default=0)
    cache_creation_tokens: int = Field(default=0)
    model: str = Field(default="")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class SSEEvent(BaseModel):
    """Server-sent event with sequencing."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence: int = Field(description="Monotonic counter for recovery")
    event_type: str = Field(description="Event type")
    data: dict[str, Any] = Field(default_factory=dict)
    sheet_version: int = Field(description="Current ScenarioSheet version")
    sheet_hash: str = Field(description="For change detection")
    token_usage: TokenUsage | None = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Session State
# =============================================================================


class DeliberationRound(BaseModel):
    """A single round of deliberation."""

    round_number: int = Field(description="Round number (1-indexed)")
    consilium_contributions: list[ExpertContribution] = Field(default_factory=list)
    redteam_objections: list[RedTeamObjection] = Field(default_factory=list)
    filtered_objections: list[FilteredObjection] = Field(default_factory=list)
    sheet_before: ScenarioSheet | None = Field(default=None)
    sheet_after: ScenarioSheet | None = Field(default=None)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class SessionState(BaseModel):
    """Full session state for persistence."""

    session_id: UUID = Field(default_factory=uuid4)
    status: SessionStatus = Field(default=SessionStatus.CREATED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Interrogation
    core_answers: CoreInterrogation | None = Field(default=None)
    expert_interrogation: ExpertInterrogation = Field(default_factory=ExpertInterrogation)

    # Deliberation
    current_round: int = Field(default=0)
    max_rounds: int = Field(default=3)
    rounds: list[DeliberationRound] = Field(default_factory=list)

    # State
    sheet: ScenarioSheet | None = Field(default=None)
    sse_sequence: int = Field(default=0, description="Next SSE sequence number")

    # Totals
    total_token_usage: TokenUsage = Field(default_factory=TokenUsage)

    def next_sse_sequence(self) -> int:
        """Get and increment SSE sequence."""
        seq = self.sse_sequence
        self.sse_sequence += 1
        return seq

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


# =============================================================================
# API Request/Response Models
# =============================================================================


class CreateScenarioRequest(BaseModel):
    """Request to create a new scenario."""

    # Initial context (optional, will trigger interrogation if missing)
    initial_prompt: str = Field(default="", description="Free-form scenario description")


class CreateScenarioResponse(BaseModel):
    """Response after creating scenario."""

    session_id: UUID
    status: SessionStatus
    core_questions: list[dict[str, Any]] = Field(
        default_factory=list, description="Core questions to answer"
    )


class SubmitAnswersRequest(BaseModel):
    """Request to submit interrogation answers."""

    core_answers: CoreInterrogation
    expert_answers: dict[str, str] = Field(
        default_factory=dict, description="Answers to expert questions"
    )


class SubmitAnswersResponse(BaseModel):
    """Response after submitting answers."""

    session_id: UUID
    status: SessionStatus
    expert_questions: list[ExpertQuestion] = Field(
        default_factory=list, description="Follow-up expert questions"
    )
    ready_to_deliberate: bool = Field(default=False)


class ScenarioOutputResponse(BaseModel):
    """Final scenario output."""

    session_id: UUID
    status: SessionStatus
    sheet: ScenarioSheet
    narrative: str = Field(default="", description="Full narrative output")
    total_token_usage: TokenUsage


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.1.0"


class ConfigResponse(BaseModel):
    """Configuration options response."""

    eras: list[dict[str, str]]
    terrain_types: list[dict[str, str]]
    violence_levels: list[dict[str, str]]
    commander_competence: list[dict[str, str]]
    narrative_outcomes: list[dict[str, str]]


# =============================================================================
# Consistency Models
# =============================================================================


class ConsistencyViolation(BaseModel):
    """A detected consistency violation."""

    field: str = Field(description="Field with violation")
    violation_type: str = Field(description="Type of violation")
    description: str = Field(description="Description of the issue")
    severity: Literal["error", "warning"] = Field(description="Severity level")
    suggestion: str = Field(default="", description="Suggested fix")
