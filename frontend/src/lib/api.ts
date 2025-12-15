import type {
  CreateScenarioResponse,
  SubmitAnswersResponse,
  CoreAnswers,
  ScenarioOutput,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export interface ScenarioInput {
  prompt: string;
  options?: {
    era?: string;
    magic_present?: boolean;
  };
}

export async function createScenario(
  input: ScenarioInput
): Promise<CreateScenarioResponse> {
  const res = await fetch(`${API_BASE}/api/scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error);
  }
  return res.json();
}

export async function submitAnswers(
  sessionId: string,
  coreAnswers: CoreAnswers,
  expertAnswers: Record<string, string> = {}
): Promise<SubmitAnswersResponse> {
  const res = await fetch(`${API_BASE}/api/scenario/${sessionId}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      core_answers: coreAnswers,
      expert_answers: expertAnswers,
    }),
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error);
  }
  return res.json();
}

export async function getSession(sessionId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/scenario/${sessionId}`);
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error);
  }
  return res.json();
}

export async function getOutput(sessionId: string): Promise<ScenarioOutput> {
  const res = await fetch(`${API_BASE}/api/output/${sessionId}`);
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error);
  }
  return res.json();
}

export async function getConfig(): Promise<{
  eras: { value: string; label: string }[];
  terrain_types: { value: string; label: string }[];
  violence_levels: { value: string; label: string }[];
  commander_competence: { value: string; label: string }[];
  narrative_outcomes: { value: string; label: string }[];
}> {
  const res = await fetch(`${API_BASE}/api/config`);
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error);
  }
  return res.json();
}

export function getDeliberationStreamUrl(sessionId: string): string {
  return `${API_BASE}/api/deliberate/${sessionId}`;
}
