"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { getOutput } from "@/lib/api";
import type { ScenarioOutput } from "@/lib/types";

export default function OutputPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [output, setOutput] = useState<ScenarioOutput | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadOutput() {
      try {
        const data = await getOutput(sessionId);
        setOutput(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load output");
      } finally {
        setIsLoading(false);
      }
    }

    loadOutput();
  }, [sessionId]);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <div className="animate-pulse text-war-accent">Loading analysis results...</div>
      </div>
    );
  }

  if (error || !output) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <p className="text-red-500 mb-4">{error || "No output available"}</p>
        <Button onClick={() => router.push("/")}>Start New Analysis</Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-war-text mb-2">Analysis Results</h1>
            <p className="text-war-muted">
              Session: {sessionId}
            </p>
          </div>
          <Badge
            variant={output.certified ? "default" : "destructive"}
            className={output.certified ? "war-glow" : ""}
          >
            {output.certified ? "Certified" : "Not Certified"}
          </Badge>
        </div>
      </div>

      <Tabs defaultValue="summary" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="summary">Summary</TabsTrigger>
          <TabsTrigger value="analysis">Full Analysis</TabsTrigger>
          <TabsTrigger value="objections">Objections</TabsTrigger>
          <TabsTrigger value="metadata">Metadata</TabsTrigger>
        </TabsList>

        {/* Summary Tab */}
        <TabsContent value="summary">
          <div className="grid gap-6">
            {/* Certification Status */}
            <Card className={`war-panel ${output.certified ? "war-glow border-war-accent" : "border-red-600"}`}>
              <CardHeader>
                <CardTitle className={output.certified ? "text-war-accent" : "text-red-500"}>
                  {output.certified ? "Analysis Certified" : "Certification Failed"}
                </CardTitle>
                <CardDescription>
                  {output.certified
                    ? "This analysis has passed red team review and is considered reliable."
                    : "This analysis did not pass red team scrutiny. Review objections for details."}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                  <StatCard label="Rounds" value={output.rounds_taken.toString()} />
                  <StatCard label="Expert Contributions" value={output.expert_contributions.length.toString()} />
                  <StatCard label="Objections" value={output.red_team_objections.length.toString()} />
                  <StatCard
                    label="Status"
                    value={output.certified ? "Passed" : "Failed"}
                    highlight={output.certified}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Key Findings */}
            <Card className="war-panel">
              <CardHeader>
                <CardTitle className="text-war-accent">Scenario Sheet</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-semibold text-war-text mb-2">Summary</h4>
                    <p className="text-war-muted text-sm whitespace-pre-wrap">
                      {output.scenario_sheet.summary}
                    </p>
                  </div>
                  <Separator />
                  <div>
                    <h4 className="font-semibold text-war-text mb-2">Key Factors</h4>
                    <ul className="list-disc list-inside text-war-muted text-sm space-y-1">
                      {output.scenario_sheet.key_factors.map((factor, i) => (
                        <li key={i}>{factor}</li>
                      ))}
                    </ul>
                  </div>
                  <Separator />
                  <div>
                    <h4 className="font-semibold text-war-text mb-2">Risks</h4>
                    <ul className="list-disc list-inside text-war-muted text-sm space-y-1">
                      {output.scenario_sheet.risks.map((risk, i) => (
                        <li key={i}>{risk}</li>
                      ))}
                    </ul>
                  </div>
                  <Separator />
                  <div>
                    <h4 className="font-semibold text-war-text mb-2">Recommendations</h4>
                    <ul className="list-disc list-inside text-war-muted text-sm space-y-1">
                      {output.scenario_sheet.recommendations.map((rec, i) => (
                        <li key={i}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Full Analysis Tab */}
        <TabsContent value="analysis">
          <Card className="war-panel">
            <CardHeader>
              <CardTitle className="text-war-accent">Expert Contributions</CardTitle>
              <CardDescription>
                Detailed analysis from each expert across all rounds
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px] pr-4">
                <div className="space-y-6">
                  {output.expert_contributions.map((contribution, index) => (
                    <div key={index} className="border-l-2 border-war-accent pl-4 py-2">
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
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Objections Tab */}
        <TabsContent value="objections">
          <Card className="war-panel">
            <CardHeader>
              <CardTitle className="text-red-500">Red Team Objections</CardTitle>
              <CardDescription>
                Challenges and concerns raised during deliberation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px] pr-4">
                {output.red_team_objections.length === 0 ? (
                  <p className="text-war-muted text-sm italic">
                    No objections were raised during deliberation.
                  </p>
                ) : (
                  <div className="space-y-6">
                    {output.red_team_objections.map((objection, index) => (
                      <div key={index} className="border-l-2 border-red-600 pl-4 py-2">
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
                        {objection.addressed && (
                          <p className="text-xs text-green-500 mt-2">Addressed</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Metadata Tab */}
        <TabsContent value="metadata">
          <Card className="war-panel">
            <CardHeader>
              <CardTitle className="text-war-accent">Session Metadata</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 text-sm">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-war-muted">Session ID</span>
                    <p className="text-war-text font-mono">{sessionId}</p>
                  </div>
                  <div>
                    <span className="text-war-muted">Certification Status</span>
                    <p className={output.certified ? "text-green-500" : "text-red-500"}>
                      {output.certified ? "Certified" : "Not Certified"}
                    </p>
                  </div>
                  <div>
                    <span className="text-war-muted">Total Rounds</span>
                    <p className="text-war-text">{output.rounds_taken}</p>
                  </div>
                  <div>
                    <span className="text-war-muted">Expert Count</span>
                    <p className="text-war-text">
                      {new Set(output.expert_contributions.map((c) => c.expert)).size}
                    </p>
                  </div>
                </div>
                <Separator />
                <div>
                  <span className="text-war-muted">Original Scenario</span>
                  <p className="text-war-text mt-2 whitespace-pre-wrap">
                    {output.scenario_sheet.summary}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Actions */}
      <div className="mt-8 flex justify-center gap-4">
        <Button variant="outline" onClick={() => router.push("/")}>
          Start New Analysis
        </Button>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="p-4 rounded-lg bg-war-bg">
      <p className="text-war-muted text-xs uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold ${highlight ? "text-war-accent" : "text-war-text"}`}>
        {value}
      </p>
    </div>
  );
}
