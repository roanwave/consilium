"use client";

import { useState, useCallback } from "react";
import { getDeliberationStreamUrl } from "@/lib/api";
import type { ExpertContribution, RedTeamObjection } from "@/lib/types";

export interface DeliberationState {
  status: "idle" | "connecting" | "deliberating" | "complete" | "error";
  currentRound: number;
  maxRounds: number;
  events: any[];
  contributions: ExpertContribution[];
  objections: RedTeamObjection[];
  error: string | null;
  certified: boolean;
}

export function useDeliberation(sessionId: string | null) {
  const [state, setState] = useState<DeliberationState>({
    status: "idle",
    currentRound: 0,
    maxRounds: 3,
    events: [],
    contributions: [],
    objections: [],
    error: null,
    certified: false,
  });

  const startDeliberation = useCallback(() => {
    if (!sessionId) return;

    setState((s) => ({ ...s, status: "connecting", events: [], contributions: [], objections: [] }));

    const eventSource = new EventSource(getDeliberationStreamUrl(sessionId));

    eventSource.onopen = () => {
      setState((s) => ({ ...s, status: "deliberating" }));
    };

    eventSource.onerror = () => {
      setState((s) => ({
        ...s,
        status: s.certified ? "complete" : "error",
        error: s.certified ? null : "Connection lost",
      }));
      eventSource.close();
    };

    // Generic message handler for all events
    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        const eventType = data.event_type || "unknown";

        setState((s) => {
          const newState = { ...s };
          newState.events = [...s.events, { type: eventType, data, sequence: data.sequence }];

          switch (eventType) {
            case "session_start":
              newState.status = "deliberating";
              break;

            case "round_start":
              newState.currentRound = data.data?.round || s.currentRound + 1;
              break;

            case "expert_contribution":
              if (data.data) {
                newState.contributions = [...s.contributions, data.data];
              }
              break;

            case "redteam_objection":
              if (data.data) {
                newState.objections = [...s.objections, data.data];
              }
              break;

            case "round_end":
              if (data.data?.certified) {
                newState.certified = true;
              }
              break;

            case "certified":
              newState.status = "complete";
              newState.certified = true;
              eventSource.close();
              break;

            case "certification_failed":
              newState.status = "complete";
              newState.certified = false;
              eventSource.close();
              break;

            case "session_end":
              newState.status = "complete";
              newState.certified = data.data?.success || false;
              eventSource.close();
              break;

            case "session_error":
              newState.status = "error";
              newState.error = data.data?.error || "Unknown error";
              eventSource.close();
              break;
          }

          return newState;
        });
      } catch (err) {
        console.error("Failed to parse event:", e.data, err);
      }
    };

    return () => {
      eventSource.close();
    };
  }, [sessionId]);

  return { state, startDeliberation };
}
