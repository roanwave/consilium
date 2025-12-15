export interface Question {
  id: string;
  type: "text" | "textarea" | "select" | "boolean";
  question: string;
  options?: { value: string; label: string }[];
  placeholder?: string;
  required: boolean;
  conditional?: { field: string; value: any };
  default?: any;
}

export interface ExpertQuestion {
  expert: string;
  question: string;
  context: string;
  default: string;
}

export interface CreateScenarioResponse {
  session_id: string;
  status: string;
  core_questions: Question[];
}

export interface SubmitAnswersResponse {
  session_id: string;
  status: string;
  expert_questions: ExpertQuestion[];
  ready_to_deliberate: boolean;
}

export interface CoreAnswers {
  era: string;
  theater: string;
  why_battle_now: string;
  army_sizes: string;
  terrain_type: string;
  terrain_feature: string;
  commander_competence_side_a: string;
  commander_competence_side_b: string;
  magic_present: boolean;
  magic_constraints: string;
  narrative_outcome: string;
  violence_level: string;
}

export interface ScenarioSheet {
  version: number;
  era: string;
  theater: string;
  stakes: string;
  constraints: string;
  forces: Record<string, any>;
  terrain_weather: any;
  timeline: any[];
  decision_points: any[];
  casualty_profile: any;
  aftermath: string;
  magic: any;
}

export interface ScenarioOutput {
  session_id: string;
  status: string;
  sheet: ScenarioSheet;
  narrative: string;
  total_token_usage: {
    input_tokens: number;
    output_tokens: number;
  };
}

export interface DeliberationEvent {
  sequence: number;
  type: string;
  data: any;
  sheetVersion: number;
}

export interface ExpertContribution {
  expert: string;
  chamber: string;
  domain_claims: string[];
  sheet_deltas: any[];
}

export interface RedTeamObjection {
  expert: string;
  objection_type: string;
  objection: string;
  field: string;
  suggestion: string;
}
