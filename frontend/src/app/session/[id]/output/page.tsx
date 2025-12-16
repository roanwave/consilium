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

interface ScenarioOutput {
  session_id: string;
  status: string;
  sheet: {
    version: number;
    era: string;
    theater: string;
    stakes: string;
    constraints: string[];
    forces: Record<string, any>;
    terrain_weather: any;
    timeline: any[];
    decision_points: any[];
    casualty_profile: any;
    aftermath: string;
    open_risks: string[];
    magic: any;
  };
  narrative: string;
  total_token_usage: {
    input_tokens: number;
    output_tokens: number;
    cache_read_tokens?: number;
    cache_creation_tokens?: number;
  };
}

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

  const isCertified = output.status === "certified";
  const sheet = output.sheet;

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-war-text mb-2">Scenario Results</h1>
            <p className="text-war-muted">
              Session: {sessionId.slice(0, 8)}...
            </p>
          </div>
          <Badge
            variant={isCertified ? "default" : "destructive"}
            className={isCertified ? "war-glow" : ""}
          >
            {isCertified ? "Certified" : output.status}
          </Badge>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="forces">Forces</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="details">Details</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid gap-6">
            {/* Status Card */}
            <Card className={`war-panel ${isCertified ? "war-glow border-war-accent" : "border-red-600"}`}>
              <CardHeader>
                <CardTitle className={isCertified ? "text-war-accent" : "text-red-500"}>
                  {isCertified ? "Scenario Certified" : `Status: ${output.status}`}
                </CardTitle>
                <CardDescription>
                  {isCertified
                    ? "This scenario has been validated by the expert panel."
                    : "This scenario is still being processed or encountered issues."}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                  <StatCard label="Era" value={sheet?.era?.replace("_", " ") || "N/A"} />
                  <StatCard label="Theater" value={sheet?.theater || "N/A"} />
                  <StatCard label="Version" value={sheet?.version?.toString() || "0"} />
                  <StatCard
                    label="Status"
                    value={isCertified ? "Certified" : output.status}
                    highlight={isCertified}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Stakes */}
            <Card className="war-panel">
              <CardHeader>
                <CardTitle className="text-war-accent">Battle Stakes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-war-text whitespace-pre-wrap">
                  {sheet?.stakes || "No stakes defined"}
                </p>
              </CardContent>
            </Card>

            {/* Constraints & Risks */}
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="war-panel">
                <CardHeader>
                  <CardTitle className="text-war-accent">Constraints</CardTitle>
                </CardHeader>
                <CardContent>
                  {sheet?.constraints ? (
                    <ul className="list-disc list-inside text-war-muted text-sm space-y-1">
                      {Array.isArray(sheet.constraints)
                        ? sheet.constraints.map((c: string, i: number) => (
                            <li key={i}>{c}</li>
                          ))
                        : <li>{String(sheet.constraints)}</li>
                      }
                    </ul>
                  ) : (
                    <p className="text-war-muted text-sm italic">No constraints defined</p>
                  )}
                </CardContent>
              </Card>

              <Card className="war-panel">
                <CardHeader>
                  <CardTitle className="text-war-accent">Open Risks</CardTitle>
                </CardHeader>
                <CardContent>
                  {sheet?.open_risks ? (
                    <ul className="list-disc list-inside text-war-muted text-sm space-y-1">
                      {Array.isArray(sheet.open_risks)
                        ? sheet.open_risks.map((r: string, i: number) => (
                            <li key={i}>{r}</li>
                          ))
                        : <li>{String(sheet.open_risks)}</li>
                      }
                    </ul>
                  ) : (
                    <p className="text-war-muted text-sm italic">No open risks identified</p>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Aftermath */}
            {sheet?.aftermath && (
              <Card className="war-panel">
                <CardHeader>
                  <CardTitle className="text-war-accent">Aftermath</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-war-text whitespace-pre-wrap">{sheet.aftermath}</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Forces Tab */}
        <TabsContent value="forces">
          <div className="grid gap-6">
            {sheet?.forces && Object.entries(sheet.forces).map(([sideKey, force]: [string, any]) => (
              <Card key={sideKey} className="war-panel">
                <CardHeader>
                  <CardTitle className="text-war-accent">{force.side_name || sideKey}</CardTitle>
                  <CardDescription>
                    Total Strength: {force.total_strength?.toLocaleString() || "Unknown"}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Commander */}
                  {force.commander && (
                    <div>
                      <h4 className="font-semibold text-war-text mb-2">Commander</h4>
                      <p className="text-war-muted text-sm">
                        <strong>{force.commander.name}</strong>
                        {force.commander.title && ` - ${force.commander.title}`}
                        {force.commander.competence && ` (${force.commander.competence})`}
                      </p>
                      {force.commander.known_for && (
                        <p className="text-war-muted text-xs mt-1">Known for: {force.commander.known_for}</p>
                      )}
                    </div>
                  )}

                  <Separator />

                  {/* Composition */}
                  {force.composition && Array.isArray(force.composition) && force.composition.length > 0 && (
                    <div>
                      <h4 className="font-semibold text-war-text mb-2">Unit Composition</h4>
                      <div className="space-y-2">
                        {force.composition.map((unit: any, i: number) => (
                          <div key={i} className="text-sm text-war-muted">
                            <span className="font-medium">{unit.unit_type || unit.type || 'Unit'}</span>: {unit.count?.toLocaleString() || '?'} ({unit.quality || 'unknown'})
                            {unit.notes && <span className="text-xs"> - {unit.notes}</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <Separator />

                  {/* Morale & Supply */}
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-war-muted">Morale:</span>
                      <span className="text-war-text ml-2">{force.morale || "Unknown"}</span>
                    </div>
                    <div>
                      <span className="text-war-muted">Supply:</span>
                      <span className="text-war-text ml-2">{force.supply_state || "Unknown"}</span>
                    </div>
                  </div>

                  {/* Objectives */}
                  {force.objectives && (
                    <div>
                      <h4 className="font-semibold text-war-text mb-2">Objectives</h4>
                      <ul className="list-disc list-inside text-war-muted text-sm space-y-1">
                        {Array.isArray(force.objectives)
                          ? force.objectives.map((obj: string, i: number) => (
                              <li key={i}>{obj}</li>
                            ))
                          : <li>{String(force.objectives)}</li>
                        }
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}

            {(!sheet?.forces || Object.keys(sheet.forces).length === 0) && (
              <p className="text-war-muted text-center py-8">No force data available</p>
            )}
          </div>
        </TabsContent>

        {/* Timeline Tab */}
        <TabsContent value="timeline">
          <Card className="war-panel">
            <CardHeader>
              <CardTitle className="text-war-accent">Battle Timeline</CardTitle>
              <CardDescription>Key events and decision points</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px] pr-4">
                {sheet?.timeline && Array.isArray(sheet.timeline) && sheet.timeline.length > 0 ? (
                  <div className="space-y-4">
                    {sheet.timeline.map((event: any, i: number) => (
                      <div key={i} className="border-l-2 border-war-accent pl-4 py-2">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline">{event.timestamp || event.time || 'Event'}</Badge>
                        </div>
                        <p className="text-war-text text-sm">{event.event || event.description || String(event)}</p>
                        {event.triggered_by && (
                          <p className="text-war-muted text-xs mt-1">Triggered by: {event.triggered_by}</p>
                        )}
                        {event.consequences && (
                          <div className="mt-2">
                            <p className="text-xs text-war-muted">Consequences:</p>
                            <ul className="list-disc list-inside text-xs text-war-muted">
                              {Array.isArray(event.consequences)
                                ? event.consequences.map((c: string, j: number) => (
                                    <li key={j}>{c}</li>
                                  ))
                                : <li>{String(event.consequences)}</li>
                              }
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : sheet?.timeline && typeof sheet.timeline === 'string' ? (
                  <p className="text-war-text whitespace-pre-wrap">{sheet.timeline}</p>
                ) : (
                  <p className="text-war-muted text-center py-8">No timeline events available</p>
                )}

                {sheet?.decision_points && (
                  <>
                    <Separator className="my-6" />
                    <h3 className="text-war-accent font-semibold mb-4">Decision Points</h3>
                    <div className="space-y-4">
                      {Array.isArray(sheet.decision_points) ? (
                        sheet.decision_points.map((dp: any, i: number) => (
                          <div key={i} className="border-l-2 border-yellow-500 pl-4 py-2">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant="secondary">{dp.timestamp || dp.time || 'Decision'}</Badge>
                              <span className="text-xs text-war-muted">{dp.commander}</span>
                            </div>
                            <p className="text-war-text text-sm font-medium">{dp.situation || dp.description}</p>
                            {dp.options && (
                              <div className="mt-2">
                                <p className="text-xs text-war-muted">Options:</p>
                                <ul className="list-disc list-inside text-xs text-war-muted">
                                  {Array.isArray(dp.options)
                                    ? dp.options.map((opt: string, j: number) => (
                                        <li key={j} className={opt === dp.chosen ? "text-war-accent" : ""}>
                                          {opt} {opt === dp.chosen && "(chosen)"}
                                        </li>
                                      ))
                                    : <li>{String(dp.options)}</li>
                                  }
                                </ul>
                              </div>
                            )}
                            {dp.rationale && (
                              <p className="text-xs text-war-muted mt-1">Rationale: {dp.rationale}</p>
                            )}
                          </div>
                        ))
                      ) : (
                        <p className="text-war-text text-sm">{typeof sheet.decision_points === 'object' ? JSON.stringify(sheet.decision_points) : String(sheet.decision_points)}</p>
                      )}
                    </div>
                  </>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Details Tab */}
        <TabsContent value="details">
          <div className="grid gap-6">
            {/* Terrain & Weather */}
            {sheet?.terrain_weather && (
              <Card className="war-panel">
                <CardHeader>
                  <CardTitle className="text-war-accent">Terrain & Weather</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-war-muted">Terrain Type:</span>
                      <p className="text-war-text">{sheet.terrain_weather.terrain_type?.replace("_", " ") || "Unknown"}</p>
                    </div>
                    <div>
                      <span className="text-war-muted">Weather:</span>
                      <p className="text-war-text">{sheet.terrain_weather.weather?.replace("_", " ") || "Unknown"}</p>
                    </div>
                    <div>
                      <span className="text-war-muted">Time of Day:</span>
                      <p className="text-war-text">{sheet.terrain_weather.time_of_day || "Unknown"}</p>
                    </div>
                    <div>
                      <span className="text-war-muted">Visibility:</span>
                      <p className="text-war-text">{sheet.terrain_weather.visibility || "Unknown"}</p>
                    </div>
                    <div>
                      <span className="text-war-muted">Ground:</span>
                      <p className="text-war-text">{sheet.terrain_weather.ground_conditions || "Unknown"}</p>
                    </div>
                    <div>
                      <span className="text-war-muted">Season:</span>
                      <p className="text-war-text">{sheet.terrain_weather.season || "Unknown"}</p>
                    </div>
                  </div>
                  {sheet.terrain_weather.defining_feature && (
                    <div>
                      <span className="text-war-muted text-sm">Defining Feature:</span>
                      <p className="text-war-text">{sheet.terrain_weather.defining_feature}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Casualty Profile */}
            {sheet?.casualty_profile && (
              <Card className="war-panel">
                <CardHeader>
                  <CardTitle className="text-war-accent">Casualty Profile</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-war-muted">Winner Casualties:</span>
                      <p className="text-war-text">{sheet.casualty_profile.winner_casualties_percent}%</p>
                    </div>
                    <div>
                      <span className="text-war-muted">Loser Casualties:</span>
                      <p className="text-war-text">{sheet.casualty_profile.loser_casualties_percent}%</p>
                    </div>
                  </div>
                  {sheet.casualty_profile.casualty_distribution && (
                    <div>
                      <span className="text-war-muted text-sm">Distribution:</span>
                      <p className="text-war-text text-sm">{sheet.casualty_profile.casualty_distribution}</p>
                    </div>
                  )}
                  {sheet.casualty_profile.notable_deaths && (
                    <div>
                      <span className="text-war-muted text-sm">Notable Deaths:</span>
                      <ul className="list-disc list-inside text-war-text text-sm">
                        {Array.isArray(sheet.casualty_profile.notable_deaths)
                          ? sheet.casualty_profile.notable_deaths.map((d: string, i: number) => (
                              <li key={i}>{d}</li>
                            ))
                          : <li>{String(sheet.casualty_profile.notable_deaths)}</li>
                        }
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Magic System */}
            {sheet?.magic?.present && (
              <Card className="war-panel">
                <CardHeader>
                  <CardTitle className="text-war-accent">Magic System</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {sheet.magic.tactical_role && (
                    <div>
                      <span className="text-war-muted text-sm">Tactical Role:</span>
                      <p className="text-war-text">{sheet.magic.tactical_role}</p>
                    </div>
                  )}
                  {sheet.magic.constraints && (
                    <div>
                      <span className="text-war-muted text-sm">Constraints:</span>
                      <ul className="list-disc list-inside text-war-text text-sm">
                        {Array.isArray(sheet.magic.constraints)
                          ? sheet.magic.constraints.map((c: string, i: number) => (
                              <li key={i}>{c}</li>
                            ))
                          : <li>{String(sheet.magic.constraints)}</li>
                        }
                      </ul>
                    </div>
                  )}
                  {sheet.magic.practitioners && (
                    <div>
                      <span className="text-war-muted text-sm">Practitioners:</span>
                      <ul className="list-disc list-inside text-war-text text-sm">
                        {Array.isArray(sheet.magic.practitioners)
                          ? sheet.magic.practitioners.map((p: string, i: number) => (
                              <li key={i}>{p}</li>
                            ))
                          : <li>{String(sheet.magic.practitioners)}</li>
                        }
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Token Usage */}
            <Card className="war-panel">
              <CardHeader>
                <CardTitle className="text-war-accent">Session Metadata</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-war-muted">Input Tokens</span>
                    <p className="text-war-text font-mono">{output.total_token_usage?.input_tokens?.toLocaleString() || 0}</p>
                  </div>
                  <div>
                    <span className="text-war-muted">Output Tokens</span>
                    <p className="text-war-text font-mono">{output.total_token_usage?.output_tokens?.toLocaleString() || 0}</p>
                  </div>
                  <div>
                    <span className="text-war-muted">Cache Read</span>
                    <p className="text-war-text font-mono">{output.total_token_usage?.cache_read_tokens?.toLocaleString() || 0}</p>
                  </div>
                  <div>
                    <span className="text-war-muted">Sheet Version</span>
                    <p className="text-war-text font-mono">{sheet?.version || 0}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Actions */}
      <div className="mt-8 flex justify-center gap-4">
        <Button variant="outline" onClick={() => router.push("/")}>
          Start New Scenario
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
      <p className={`text-lg font-bold ${highlight ? "text-war-accent" : "text-war-text"} capitalize`}>
        {value}
      </p>
    </div>
  );
}
