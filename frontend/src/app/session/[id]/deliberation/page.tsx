"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useDeliberation } from "@/hooks/useDeliberation";

export default function DeliberationPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const { state, startDeliberation } = useDeliberation(sessionId);

  useEffect(() => {
    startDeliberation();
  }, [startDeliberation]);

  useEffect(() => {
    if (state.status === "certified" || state.status === "failed") {
      // Navigate to output page after a short delay
      const timer = setTimeout(() => {
        router.push(`/session/${sessionId}/output`);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [state.status, sessionId, router]);

  const progressPercentage = state.maxRounds > 0
    ? (state.currentRound / state.maxRounds) * 100
    : 0;

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-war-text mb-2">Deliberation in Progress</h1>
            <p className="text-war-muted">
              Experts are analyzing and red team is challenging the analysis.
            </p>
          </div>
          <StatusBadge status={state.status} />
        </div>

        {/* Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-war-muted">
            <span>Round {state.currentRound} of {state.maxRounds}</span>
            <span>{Math.round(progressPercentage)}% Complete</span>
          </div>
          <Progress value={progressPercentage} className="h-2" />
        </div>
      </div>

      {/* Main content grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Expert Panel */}
        <Card className="war-panel">
          <CardHeader>
            <CardTitle className="text-war-accent flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-war-accent"></span>
              Expert Analysis
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[500px] pr-4">
              <div className="space-y-4">
                {state.expertContributions.length === 0 ? (
                  <p className="text-war-muted text-sm italic">
                    Waiting for expert contributions...
                  </p>
                ) : (
                  state.expertContributions.map((contribution, index) => (
                    <div key={index} className="deliberation-entry expert">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="secondary" className="capitalize">
                          {contribution.expert}
                        </Badge>
                        <span className="text-xs text-war-muted">
                          Round {contribution.round}
                        </span>
                      </div>
                      <p className="text-sm text-war-text whitespace-pre-wrap">
                        {contribution.content}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Red Team Panel */}
        <Card className="war-panel">
          <CardHeader>
            <CardTitle className="text-red-500 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500"></span>
              Red Team Challenges
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[500px] pr-4">
              <div className="space-y-4">
                {state.redTeamObjections.length === 0 ? (
                  <p className="text-war-muted text-sm italic">
                    Waiting for red team review...
                  </p>
                ) : (
                  state.redTeamObjections.map((objection, index) => (
                    <div key={index} className="deliberation-entry redteam">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="destructive" className="capitalize">
                          {objection.challenger}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {objection.severity}
                        </Badge>
                        <span className="text-xs text-war-muted">
                          Round {objection.round}
                        </span>
                      </div>
                      <p className="text-sm text-war-text whitespace-pre-wrap">
                        {objection.objection}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Status Footer */}
      {state.status === "certified" && (
        <div className="mt-8 p-6 war-panel war-glow-strong border-war-accent text-center">
          <h2 className="text-2xl font-bold text-war-accent mb-2">Analysis Certified</h2>
          <p className="text-war-muted">
            The scenario has passed red team review. Redirecting to results...
          </p>
        </div>
      )}

      {state.status === "failed" && (
        <div className="mt-8 p-6 war-panel border-red-600 text-center">
          <h2 className="text-2xl font-bold text-red-500 mb-2">Certification Failed</h2>
          <p className="text-war-muted">
            The analysis could not be certified after maximum rounds. Redirecting to results...
          </p>
        </div>
      )}

      {state.error && (
        <div className="mt-8 p-6 war-panel border-red-600 text-center">
          <h2 className="text-xl font-bold text-red-500 mb-2">Error</h2>
          <p className="text-war-muted">{state.error}</p>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
    idle: { variant: "outline", label: "Idle" },
    connecting: { variant: "secondary", label: "Connecting..." },
    deliberating: { variant: "default", label: "Deliberating" },
    certified: { variant: "default", label: "Certified" },
    failed: { variant: "destructive", label: "Failed" },
    error: { variant: "destructive", label: "Error" },
  };

  const config = variants[status] || variants.idle;

  return (
    <Badge variant={config.variant} className={status === "deliberating" ? "animate-pulse" : ""}>
      {config.label}
    </Badge>
  );
}
